"""Seed the investment thesis (BUILD_SPEC §14 Phase 1). Thesis rows are append-only: a change in code adds a version."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import thesis as T
from .models import Thesis


def _current(db: Session) -> Thesis | None:
    return db.execute(select(Thesis).order_by(Thesis.created_at.desc())).scalars().first()


def seed_thesis(db: Session) -> Thesis:
    fingerprint = T.thesis_fingerprint()
    existing = _current(db)
    if existing and (existing.criteria_json or {}).get("fingerprint") == fingerprint:
        return existing
    row = Thesis(
        name=T.THESIS_NAME,
        thesis_text=T.THESIS_TEXT,
        criteria_json={**T.criteria_payload(), "fingerprint": fingerprint},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_thesis(db: Session) -> Thesis:
    return seed_thesis(db)
