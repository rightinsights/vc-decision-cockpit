from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..llm import LLMClient, LLMError, get_llm
from ..models import Company
from ..schemas import ResearchOut, ResearchRequest
from ..services.brave import BraveClient, ResearchError, get_brave
from ..services.research import latest_research, research_view, run_research
from .deps import get_company

router = APIRouter(tags=["research"])


@router.post("/companies/{company_id}/research", response_model=ResearchOut)
async def research(
    payload: ResearchRequest | None = None,
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    brave: BraveClient | None = Depends(get_brave),
) -> ResearchOut:
    if brave is None:
        raise HTTPException(status_code=400, detail="BRAVE_API_KEY is not set. Add it to backend/.env to enable public research.")
    try:
        return await run_research(db, company, llm, brave, payload.brief if payload else None)
    except ResearchError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Search failure: {exc}") from exc
    except LLMError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"LLM failure: {exc}") from exc


@router.get("/companies/{company_id}/research", response_model=ResearchOut)
def read_research(company: Company = Depends(get_company), db: Session = Depends(get_db)) -> ResearchOut:
    run = latest_research(db, company.id)
    if run is None:
        raise HTTPException(status_code=404, detail="No research has been run for this company.")
    return research_view(run)
