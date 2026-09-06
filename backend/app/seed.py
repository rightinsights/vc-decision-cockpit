"""Seed the investment thesis (BUILD_SPEC §14 Phase 1)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import thesis as T
from .models import Thesis


def seed_thesis(db: Session) -> Thesis:
    existing = db.execute(select(Thesis).order_by(Thesis.created_at)).scalars().first()
    if existing:
        return existing
    row = Thesis(
        name=T.THESIS_NAME,
        thesis_text=T.THESIS_TEXT,
        criteria_json={
            "criteria": T.CRITERIA,
            "positive_signals": T.POSITIVE_SIGNALS,
            "out_of_scope": T.OUT_OF_SCOPE,
            "bands": [{"min": floor, "recommendation": label} for floor, label in T.BANDS],
        },
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_thesis(db: Session) -> Thesis:
    return seed_thesis(db)
