"""Before -> new evidence -> after. Shared by the agent check and the founder-note reassessment."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..llm import LLMClient
from ..llm_schemas import NoteAnalysis
from ..models import Assessment, Company, Decision, Evidence, FounderNote, MonitoringEvent
from ..schemas import AssessmentOut, DecisionOut, EvidenceOut, MonitoringEventOut, ReassessmentOut, RecommendationChange
from ..scoring import diff_scores
from ..thesis import LABELS
from .analysis import AnalysisError, claims_block, company_claims, latest_assessment, latest_decision, run_assessment, snapshot_json

_WORD = re.compile(r"[a-z0-9]{4,}")


def match_claim_id(db: Session, company_id: str, text: str | None) -> str | None:
    """Best-effort mapping of free text onto an existing claim by shared meaningful words."""
    if not text:
        return None
    wanted = set(_WORD.findall(text.lower()))
    best_id, best_hits = None, 1
    for claim in company_claims(db, company_id):
        hits = len(wanted & set(_WORD.findall(claim.claim_text.lower())))
        if hits > best_hits:
            best_id, best_hits = claim.id, hits
    return best_id


def _host(url: str | None) -> str:
    if not url:
        return "the agent"
    return urlparse(url).hostname or url


def explain(
    *, trigger: str, event: MonitoringEvent | None, note_summary: str | None, deltas: list[dict[str, Any]],
    before: Assessment | None, after: Assessment, decision: Decision | None, new_evidence_count: int,
) -> tuple[bool, str]:
    parts: list[str] = []
    if trigger == "AGENT":
        if event is None or not event.event_found:
            parts.append("The agent found nothing material since the last review.")
        else:
            parts.append(f"New evidence from {_host(event.source_url)}: {event.summary}")
            if event.claim_or_gap_affected:
                parts.append(f"It bears on: {event.claim_or_gap_affected}.")
    elif trigger == "RESEARCH":
        parts.append(f"Public research added {new_evidence_count} sourced fact{'s' if new_evidence_count != 1 else ''} as evidence.")
        if note_summary:
            parts.append(note_summary)
    else:
        parts.append(f"Founder update added {new_evidence_count} piece{'s' if new_evidence_count != 1 else ''} of evidence.")
        if note_summary:
            parts.append(note_summary)

    if deltas:
        moved = "; ".join(f"{d['label']} {d['old'] if d['old'] is not None else 'n/a'} to {d['new'] if d['new'] is not None else 'n/a'}" for d in deltas)
        parts.append(f"Criterion changes: {moved}.")
    else:
        parts.append("No criterion score moved.")

    rec_before = before.recommendation if before else None
    if rec_before != after.recommendation:
        parts.append(f"AI recommendation: {rec_before or 'none'} to {after.recommendation or 'none'}.")
    else:
        parts.append(f"AI recommendation stays {after.recommendation or 'unset'}.")

    if decision:
        parts.append(f"Your decision remains {decision.decision} until you change it.")
    else:
        parts.append("No human decision has been recorded yet.")

    matters = bool(deltas) or rec_before != after.recommendation or bool(event and event.suggested_action == "REVIEW")
    return matters, " ".join(parts)


def build_reassessment(
    db: Session, company: Company, *, trigger: str, before: Assessment | None, after: Assessment,
    event: MonitoringEvent | None, note_summary: str | None, new_evidence: list[Evidence],
) -> ReassessmentOut:
    decision = latest_decision(db, company.id)
    deltas = diff_scores(before.criterion_scores_json if before else {}, after.criterion_scores_json) if before is not after else []
    matters, text = explain(
        trigger=trigger, event=event, note_summary=note_summary, deltas=deltas, before=before, after=after,
        decision=decision, new_evidence_count=len(new_evidence),
    )
    rec_before = before.recommendation if before else None
    return ReassessmentOut(
        trigger=trigger,  # type: ignore[arg-type]
        event=MonitoringEventOut.model_validate(event) if event else None,
        note_summary=note_summary,
        new_evidence=[EvidenceOut.model_validate(e) for e in new_evidence],
        assessment_before=AssessmentOut.model_validate(before) if before else None,
        assessment_after=AssessmentOut.model_validate(after),
        deltas=[dict(d) for d in deltas],
        recommendation=RecommendationChange(before=rec_before, after=after.recommendation, changed=rec_before != after.recommendation),
        human_decision=DecisionOut.model_validate(decision) if decision else None,
        matters=matters,
        explanation=text,
    )


def analyze_founder_note(db: Session, company: Company, llm: LLMClient, note: FounderNote) -> ReassessmentOut:
    before = latest_assessment(db, company.id)
    if before is None:
        raise AnalysisError("Run the deck analysis before adding founder notes.")
    analysis = llm.parse(
        "note_analysis",
        {"snapshot": snapshot_json(company), "claims_block": claims_block(db, company.id), "notes": note.raw_notes},
        NoteAnalysis,
    )
    valid_claim_ids = {c.id for c in company_claims(db, company.id)}
    new_evidence: list[Evidence] = []
    for item in analysis.new_evidence:
        claim_id = item.claim_id if item.claim_id in valid_claim_ids else match_claim_id(db, company.id, item.evidence_text)
        row = Evidence(
            company_id=company.id, claim_id=claim_id, evidence_text=item.evidence_text, relation=item.relation,
            source_type="FOUNDER_NOTE", source_ref_id=note.id,
        )
        db.add(row)
        new_evidence.append(row)
    db.flush()
    note.analysis_json = analysis.model_dump()

    lines = [f"FOUNDER NOTE ({note.created_at.date().isoformat()}): {note.raw_notes}"]
    for item in analysis.new_evidence:
        target = f" on criterion {LABELS.get(item.criterion, item.criterion)}" if item.criterion else ""
        lines.append(f"- {item.relation}{target}: {item.evidence_text}")
    for contradiction in analysis.contradictions:
        lines.append(f"- CONTRADICTION: {contradiction}")
    after = run_assessment(db, company, llm, trigger="FOUNDER_NOTE", source_ref_id=note.id, extra_context="\n".join(lines))
    db.commit()
    for row in new_evidence:
        db.refresh(row)
    return build_reassessment(
        db, company, trigger="FOUNDER_NOTE", before=before, after=after, event=None,
        note_summary=analysis.summary, new_evidence=new_evidence,
    )
