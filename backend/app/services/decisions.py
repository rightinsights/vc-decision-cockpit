"""Human decisions are append-only and never changed by the system (BUILD_SPEC §5, §11)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company, Decision
from ..schemas import DecisionCreate
from .analysis import latest_assessment


def record_decision(db: Session, company: Company, payload: DecisionCreate) -> Decision:
    assessment = latest_assessment(db, company.id)
    row = Decision(
        company_id=company.id,
        assessment_id=assessment.id if assessment else None,
        decision=payload.decision,
        rationale=payload.rationale,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_decisions(db: Session, company_id: str) -> list[Decision]:
    stmt = select(Decision).where(Decision.company_id == company_id).order_by(Decision.created_at.desc())
    return list(db.execute(stmt).scalars().all())
