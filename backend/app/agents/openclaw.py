"""
OpenClaw adapter. Uses the gateway's OpenAI-compatible endpoint, the one synchronous path that
returns the agent's reply text:

    POST {gateway}/v1/chat/completions
    Authorization: Bearer <gateway token>
    {"model": "openclaw/<agentId>", "messages": [...], "stream": false}

Requires `gateway.http.endpoints.chatCompletions.enabled: true` in the OpenClaw config.
Docs: https://docs.openclaw.ai/gateway/openai-http-api
"""

from __future__ import annotations

import logging

import httpx

from .base import AgentError, AgentFinding, AgentRequest, build_task, parse_finding

log = logging.getLogger("agent.openclaw")


class OpenClawMonitoringAgent:
    name = "openclaw"

    def __init__(
        self,
        gateway_url: str | None,
        token: str | None,
        agent_id: str = "main",
        timeout_seconds: int = 300,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not gateway_url:
            raise AgentError("OPENCLAW_GATEWAY_URL is not set.")
        if not token:
            raise AgentError("OPENCLAW_GATEWAY_TOKEN is not set.")
        self.gateway_url = gateway_url.rstrip("/")
        self.token = token
        self.agent_id = agent_id
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def build_request(self, request: AgentRequest) -> tuple[str, dict, dict]:
        system, user = build_task(request)
        body = {
            "model": f"openclaw/{self.agent_id}",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "x-openclaw-agent-id": self.agent_id,
        }
        return f"{self.gateway_url}/v1/chat/completions", body, headers

    async def check_company(self, request: AgentRequest) -> AgentFinding:
        url, body, headers = self.build_request(request)
        timeout = httpx.Timeout(self.timeout_seconds, connect=15)
        async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
            try:
                response = await client.post(url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                raise AgentError(f"Could not reach the OpenClaw gateway at {self.gateway_url}: {exc}") from exc
        if response.status_code >= 400:
            raise AgentError(f"OpenClaw gateway returned {response.status_code}: {response.text[:300]}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AgentError(f"Unexpected OpenClaw response shape: {response.text[:300]}") from exc
        log.info("openclaw reply chars=%d", len(content or ""))
        return parse_finding(content or "")
