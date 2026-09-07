from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..llm import LLMClient, LLMError, get_llm
from ..models import Company
from ..schemas import ResearchOut, ResearchRequest
from ..services.brave import BraveClient, ResearchError, get_brave
from ..services.research import latest_research, research_view, run_research
from .deps import get_company
from .longrun import stream_json

router = APIRouter(tags=["research"])


@router.post("/companies/{company_id}/research", response_model=ResearchOut)
def research(
    payload: ResearchRequest | None = None,
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    brave: BraveClient | None = Depends(get_brave),
) -> StreamingResponse:
    if brave is None:
        raise HTTPException(status_code=400, detail="BRAVE_API_KEY is not set. Add it to backend/.env to enable public research.")
    brief = payload.brief if payload else None

    def work() -> ResearchOut:
        try:
            return asyncio.run(run_research(db, company, llm, brave, brief))
        except ResearchError as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"Search failure: {exc}") from exc
        except LLMError as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"LLM failure: {exc}") from exc

    return stream_json(work)


@router.get("/companies/{company_id}/research", response_model=ResearchOut)
def read_research(company: Company = Depends(get_company), db: Session = Depends(get_db)) -> ResearchOut:
    run = latest_research(db, company.id)
    if run is None:
        raise HTTPException(status_code=404, detail="No research has been run for this company.")
    return research_view(run)
