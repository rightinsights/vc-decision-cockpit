from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..llm import LLMClient, LLMError, get_llm
from ..models import Company
from ..schemas import AnalysisOut, QuestionOut
from ..services.analysis import AnalysisError, analyze_company, build_analysis
from ..services.questions import generate_questions
from .deps import get_company

router = APIRouter(tags=["analysis"])


@router.post("/companies/{company_id}/analyze", response_model=AnalysisOut)
def analyze(
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
) -> AnalysisOut:
    try:
        analyze_company(db, company, llm)
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM failure: {exc}") from exc
    return build_analysis(db, company)


@router.get("/companies/{company_id}/analysis", response_model=AnalysisOut)
def read_analysis(company: Company = Depends(get_company), db: Session = Depends(get_db)) -> AnalysisOut:
    return build_analysis(db, company)


@router.post("/companies/{company_id}/meeting-questions", response_model=list[QuestionOut])
def meeting_questions(
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
) -> list[QuestionOut]:
    try:
        rows = generate_questions(db, company, llm)
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM failure: {exc}") from exc
    return [QuestionOut.model_validate(r) for r in rows]
