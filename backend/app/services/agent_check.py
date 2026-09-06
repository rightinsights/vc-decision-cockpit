"""Run Agent Check (BUILD_SPEC §10): agent -> monitoring_event -> evidence -> fresh assessment -> diff."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..agents.base import AgentRequest, MonitoringAgent
from ..llm import LLMClient
from ..models import Company, Evidence, MonitoringEvent
from ..schemas import ReassessmentOut
from .analysis import AnalysisError, company_claims, latest_assessment, latest_decision, run_assessment
from .reassess import build_reassessment, match_claim_id

STRENGTH_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def open_gap_for(db: Session, company: Company) -> str:
    """The weakest claim that still lists a missing proof, phrased as a gap."""
    candidates = [c for c in company_claims(db, company.id) if c.missing_proof]
    if not candidates:
        return "No specific evidence gap recorded."
    weakest = sorted(candidates, key=lambda c: STRENGTH_ORDER.get(c.evidence_strength, 1))[0]
    return f"Claim \"{weakest.claim_text}\" lacks: {weakest.missing_proof}"


def default_question(concern: str) -> str:
    return f"Is there new external evidence that resolves this concern: {concern.rstrip('.')}?"


async def run_agent_check(
    db: Session, company: Company, llm: LLMClient, agent: MonitoringAgent, investment_question: str | None,
) -> ReassessmentOut:
    before = latest_assessment(db, company.id)
    if before is None:
        raise AnalysisError("Run the deck analysis before an agent check.")
    decision = latest_decision(db, company.id)
    if decision is None or decision.decision not in ("WATCH", "DILIGENCE"):
        raise AnalysisError("Agent checks run for companies marked WATCH or DILIGENCE. Record that decision first.")

    concern = before.main_concern or "No stated concern."
    question = (investment_question or "").strip() or default_question(concern)
    request = AgentRequest(
        company_name=company.name,
        website=company.website,
        concern=concern,
        open_gap=open_gap_for(db, company),
        last_review_date=decision.created_at.date().isoformat(),
        investment_question=question,
    )
    finding = await agent.check_company(request)

    event = MonitoringEvent(
        company_id=company.id,
        agent_provider=agent.name,
        investment_question=question,
        event_found=finding.event_found,
        event_type=finding.event_type,
        event_date=finding.date,
        summary=finding.summary,
        source_url=finding.source_url,
        relevance=finding.relevance,
        claim_or_gap_affected=finding.claim_or_gap_affected,
        suggested_action=finding.suggested_action,
        raw_json=finding.model_dump(),
    )
    db.add(event)
    db.flush()

    new_evidence: list[Evidence] = []
    after = before
    if finding.event_found and finding.summary:
        row = Evidence(
            company_id=company.id,
            claim_id=match_claim_id(db, company.id, finding.claim_or_gap_affected or finding.summary),
            evidence_text=finding.summary,
            relation=finding.relation,
            source_url=finding.source_url,
            source_type="AGENT",
            source_ref_id=event.id,
        )
        db.add(row)
        db.flush()
        new_evidence.append(row)
        extra = (
            f"AGENT FINDING ({finding.event_type}, {finding.date or 'date unknown'}): {finding.summary}\n"
            f"Source: {finding.source_url or 'none given'}\n"
            f"Relation to existing claims: {finding.relation}\n"
            f"Relevance: {finding.relevance}\n"
            f"Affects: {finding.claim_or_gap_affected or 'not specified'}"
        )
        after = run_assessment(db, company, llm, trigger="AGENT", source_ref_id=event.id, extra_context=extra)

    db.commit()
    db.refresh(event)
    for row in new_evidence:
        db.refresh(row)
    return build_reassessment(
        db, company, trigger="AGENT", before=before, after=after, event=event, note_summary=None, new_evidence=new_evidence,
    )
