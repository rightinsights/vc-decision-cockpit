"""
One LLM provider (OpenAI) behind a tiny client. Prompts live in app/prompts/*.md with
`## System` / `## User` sections and `{{variable}}` placeholders. Every call is parsed into
a strict Pydantic schema; nothing is persisted from an invalid response.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from fastapi import Depends
from pydantic import BaseModel

from .config import Settings, get_settings

log = logging.getLogger("llm")
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


@lru_cache
def _read_prompt(name: str) -> tuple[str, str]:
    text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    if "## User" not in text:
        raise LLMError(f"prompt {name} lacks a '## User' section")
    system_part, user_part = text.split("## User", 1)
    system = system_part.replace("## System", "", 1).strip()
    return system, user_part.strip()


def render_prompt(name: str, variables: dict[str, str]) -> tuple[str, str]:
    system, user = _read_prompt(name)
    for key, value in variables.items():
        token = "{{" + key + "}}"
        system = system.replace(token, value)
        user = user.replace(token, value)
    return system, user


class LLMClient:
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not set.")
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.llm_temperature

    def parse(self, prompt_name: str, variables: dict[str, str], schema: type[T]) -> T:
        system, user = render_prompt(prompt_name, variables)
        kwargs: dict = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": schema,
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        started = time.perf_counter()
        try:
            completion = self._client.chat.completions.parse(**kwargs)
        except Exception as exc:  # SDK raises many types; surface one
            raise LLMError(f"{prompt_name}: {exc}") from exc
        message = completion.choices[0].message
        if getattr(message, "refusal", None):
            raise LLMError(f"{prompt_name}: model refused: {message.refusal}")
        if message.parsed is None:
            raise LLMError(f"{prompt_name}: model returned no parsable output")
        usage = completion.usage
        log.info(
            "llm prompt=%s model=%s in=%s out=%s ms=%d",
            prompt_name, completion.model,
            getattr(usage, "prompt_tokens", "?"), getattr(usage, "completion_tokens", "?"),
            int((time.perf_counter() - started) * 1000),
        )
        return message.parsed


class FakeLLM:
    """Test double. `responses` maps schema class -> instance or list of instances (consumed in order)."""

    def __init__(self, responses: dict[type[BaseModel], BaseModel | list[BaseModel]]):
        self._responses = {k: (list(v) if isinstance(v, list) else v) for k, v in responses.items()}
        self.calls: list[tuple[str, dict[str, str]]] = []

    def parse(self, prompt_name: str, variables: dict[str, str], schema: type[T]) -> T:
        render_prompt(prompt_name, variables)  # prove the prompt file exists and renders
        self.calls.append((prompt_name, variables))
        canned = self._responses.get(schema)
        if canned is None:
            raise LLMError(f"FakeLLM has no response for {schema.__name__}")
        if isinstance(canned, list):
            if not canned:
                raise LLMError(f"FakeLLM responses for {schema.__name__} exhausted")
            return canned.pop(0)  # type: ignore[return-value]
        return canned  # type: ignore[return-value]


def get_llm(settings: Settings = Depends(get_settings)) -> LLMClient:
    return LLMClient(settings)
