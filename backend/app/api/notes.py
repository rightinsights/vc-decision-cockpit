from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..llm import LLMClient, LLMError, get_llm
from ..models import Company, FounderNote
from ..schemas import FounderNoteCreate, FounderNoteOut, ReassessmentOut
from ..services.analysis import AnalysisError
from ..services.reassess import analyze_founder_note
from .deps import get_company

router = APIRouter(tags=["founder-notes"])


class ReassessRequest(BaseModel):
    note_id: str


@router.post("/companies/{company_id}/founder-notes", response_model=FounderNoteOut, status_code=201)
def create_note(payload: FounderNoteCreate, company: Company = Depends(get_company), db: Session = Depends(get_db)) -> FounderNote:
    note = FounderNote(company_id=company.id, raw_notes=payload.raw_notes.strip())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.post("/companies/{company_id}/reassess", response_model=ReassessmentOut)
def reassess(
    payload: ReassessRequest,
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
) -> ReassessmentOut:
    note = db.get(FounderNote, payload.note_id)
    if note is None or note.company_id != company.id:
        raise HTTPException(status_code=404, detail="Founder note not found.")
    try:
        return analyze_founder_note(db, company, llm, note)
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM failure: {exc}") from exc
