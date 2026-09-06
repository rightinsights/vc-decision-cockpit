"""Monitoring agent contract (BUILD_SPEC §10). The agent supplies evidence; it never changes a decision."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from ..config import Settings, get_settings
from ..llm import render_prompt

EVENT_TYPES = ("FUNDING", "CUSTOMER", "PARTNERSHIP", "PRODUCT", "HIRING", "LAYOFFS", "FOUNDER",
               "COMPETITOR", "PATENT", "PRICING", "OTHER", "NONE")


class AgentError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentRequest:
    company_name: str
    website: str | None
    concern: str
    open_gap: str
    last_review_date: str
    investment_question: str


class AgentFinding(BaseModel):
    """Lenient parse of the agent's JSON reply (the agent is not a strict-schema model)."""

    model_config = ConfigDict(extra="ignore")

    event_found: bool
    event_type: str = "NONE"
    date: str | None = None
    summary: str = ""
    source_url: str | None = None
    relevance: str = ""
    claim_or_gap_affected: str | None = None
    suggested_action: Literal["NO_CHANGE", "REVIEW"] = "NO_CHANGE"
    relation: Literal["SUPPORTS", "CONTRADICTS", "QUALIFIES"] = "SUPPORTS"

    @field_validator("event_type", mode="before")
    @classmethod
    def _norm_type(cls, value: object) -> str:
        text = str(value or "NONE").strip().upper().replace(" ", "_")
        return text if text in EVENT_TYPES else "OTHER"

    @field_validator("source_url", mode="before")
    @classmethod
    def _norm_url(cls, value: object) -> str | None:
        if not value or not isinstance(value, str):
            return None
        value = value.strip()
        return value if value.startswith(("http://", "https://")) else None


class MonitoringAgent(Protocol):
    name: str

    async def check_company(self, request: AgentRequest) -> AgentFinding: ...


def build_task(request: AgentRequest) -> tuple[str, str]:
    """(system, user) text for the agent, from prompts/agent_task.md."""
    return render_prompt("agent_task", {
        "company_name": request.company_name,
        "website": request.website or "unknown",
        "concern": request.concern,
        "open_gap": request.open_gap,
        "last_review_date": request.last_review_date,
        "investment_question": request.investment_question,
    })


_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_finding(text: str) -> AgentFinding:
    """Accept a fenced JSON block, a bare JSON object, or JSON embedded in prose."""
    candidates: list[str] = [m.group(1) for m in _FENCE.finditer(text)]
    stripped = text.strip()
    if stripped.startswith("{"):
        candidates.insert(0, stripped)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return AgentFinding.model_validate(json.loads(candidate))
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise AgentError(f"Agent reply did not contain a valid finding JSON: {last_error}. Reply was: {text[:400]}")


def get_agent(settings: Settings = Depends(get_settings)) -> MonitoringAgent:
    if settings.agent_provider == "openclaw":
        from .openclaw import OpenClawMonitoringAgent

        return OpenClawMonitoringAgent(
            gateway_url=settings.openclaw_gateway_url,
            token=settings.openclaw_gateway_token,
            agent_id=settings.openclaw_agent_id,
            timeout_seconds=settings.openclaw_timeout_seconds,
        )
    from .mock import MockMonitoringAgent

    return MockMonitoringAgent()
