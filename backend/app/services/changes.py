"""What Changed timeline (BUILD_SPEC §5 Screen 3): every event in order, with before/after on reassessments."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Assessment, Company, Decision, DiligenceQuestion, Document, FounderNote, MonitoringEvent
from ..schemas import ChangeEntry
from ..scoring import diff_scores

TRIGGER_TITLE = {
    "DECK": "Initial deck analysis",
    "AGENT": "AI view updated after agent finding",
    "FOUNDER_NOTE": "AI view updated after founder update",
}


def _decision_at(decisions: list[Decision], when: datetime) -> str | None:
    current = None
    for d in decisions:  # ascending
        if d.created_at <= when:
            current = d.decision
        else:
            break
    return current


def build_timeline(db: Session, company: Company) -> list[ChangeEntry]:
    cid = company.id
    documents = db.execute(select(Document).where(Document.company_id == cid).order_by(Document.created_at)).scalars().all()
    assessments = db.execute(select(Assessment).where(Assessment.company_id == cid).order_by(Assessment.created_at)).scalars().all()
    decisions = list(db.execute(select(Decision).where(Decision.company_id == cid).order_by(Decision.created_at)).scalars().all())
    events = db.execute(select(MonitoringEvent).where(MonitoringEvent.company_id == cid).order_by(MonitoringEvent.created_at)).scalars().all()
    notes = db.execute(select(FounderNote).where(FounderNote.company_id == cid).order_by(FounderNote.created_at)).scalars().all()
    questions = db.execute(select(DiligenceQuestion).where(DiligenceQuestion.company_id == cid).order_by(DiligenceQuestion.created_at)).scalars().all()

    entries: list[ChangeEntry] = []
    for doc in documents:
        entries.append(ChangeEntry(
            id=doc.id, ts=doc.created_at, kind="DECK_UPLOADED", title="Deck uploaded",
            detail=f"{doc.file_name}, {doc.page_count} pages.",
        ))

    previous: Assessment | None = None
    for a in assessments:
        deltas = diff_scores(previous.criterion_scores_json, a.criterion_scores_json) if previous else []
        entries.append(ChangeEntry(
            id=a.id, ts=a.created_at, kind="ASSESSMENT", title=TRIGGER_TITLE.get(a.trigger, "AI view updated"),
            detail=a.main_concern or a.summary,
            recommendation=a.recommendation, overall_score=a.overall_score,
            deltas=[dict(d) for d in deltas],
            recommendation_before=previous.recommendation if previous else None,
            human_decision_at_time=_decision_at(decisions, a.created_at),
        ))
        previous = a

    seen_batches: set[str] = set()
    for q in questions:
        if q.assessment_id in seen_batches:
            continue
        seen_batches.add(q.assessment_id)
        entries.append(ChangeEntry(id=f"q-{q.assessment_id}", ts=q.created_at, kind="QUESTIONS",
                                   title="Five diligence questions generated", detail=q.question))

    for d in decisions:
        entries.append(ChangeEntry(
            id=d.id, ts=d.created_at, kind="DECISION", title=f"Human decision: {d.decision}", detail=d.rationale,
            recommendation=d.decision,
        ))

    for e in events:
        title = f"Agent finding: {e.event_type.replace('_', ' ').title()}" if e.event_found else "Agent check: nothing material found"
        detail = e.summary if e.event_found else f"Question asked: {e.investment_question}"
        if e.event_found and e.relevance:
            detail = f"{detail} {e.relevance}"
        entries.append(ChangeEntry(id=e.id, ts=e.created_at, kind="AGENT_EVENT", title=title, detail=detail, source_url=e.source_url,
                                   human_decision_at_time=_decision_at(decisions, e.created_at)))

    for n in notes:
        preview = n.raw_notes if len(n.raw_notes) <= 240 else n.raw_notes[:237] + "..."
        entries.append(ChangeEntry(id=n.id, ts=n.created_at, kind="FOUNDER_NOTE", title="Founder update recorded", detail=preview))

    entries.sort(key=lambda e: e.ts)
    return entries
