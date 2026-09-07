from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import thesis as T
from ..db import get_db
from ..schemas import ThesisOut
from ..seed import get_thesis

router = APIRouter(tags=["thesis"])


@router.get("/thesis", response_model=ThesisOut)
def read_thesis(db: Session = Depends(get_db)) -> ThesisOut:
    row = get_thesis(db)
    meta = row.criteria_json or {}
    return ThesisOut(
        id=row.id, name=row.name, thesis_text=row.thesis_text,
        criteria=meta.get("criteria", T.CRITERIA),
        positive_signals=meta.get("positive_signals", T.POSITIVE_SIGNALS),
        out_of_scope=meta.get("out_of_scope", T.OUT_OF_SCOPE),
        investor_note=meta.get("investor_note", T.INVESTOR_NOTE),
    )
