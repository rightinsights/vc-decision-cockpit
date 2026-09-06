"""Development stand-in for OpenClaw. Deterministic, no network."""

from __future__ import annotations

from datetime import date

from .base import AgentFinding, AgentRequest


class MockMonitoringAgent:
    name = "mock"

    async def check_company(self, request: AgentRequest) -> AgentFinding:
        slug = request.company_name.lower().replace(" ", "-").replace(":", "")
        return AgentFinding(
            event_found=True,
            event_type="CUSTOMER",
            date=date.today().isoformat(),
            summary=(
                f"{request.company_name} announced that two pilot customers have converted to paid annual "
                f"contracts, according to a company press release."
            ),
            source_url=f"https://example.com/news/{slug}-paid-contracts",
            relevance=(
                "Directly addresses the open question of whether customers are paying. "
                "Converts pilot claims from founder assertion into an externally reported fact."
            ),
            claim_or_gap_affected=request.open_gap,
            suggested_action="REVIEW",
            relation="SUPPORTS",
        )
