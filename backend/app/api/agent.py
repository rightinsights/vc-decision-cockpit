from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..agents.base import AgentError, MonitoringAgent, get_agent
from ..db import get_db
from ..llm import LLMClient, LLMError, get_llm
from ..models import Company
from ..schemas import AgentCheckRequest, ReassessmentOut
from ..services.agent_check import run_agent_check
from ..services.analysis import AnalysisError
from .deps import get_company
from .longrun import stream_json

router = APIRouter(tags=["agent"])


@router.post("/companies/{company_id}/agent-check", response_model=ReassessmentOut)
def agent_check(
    payload: AgentCheckRequest | None = None,
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    agent: MonitoringAgent = Depends(get_agent),
) -> StreamingResponse:
    question = payload.investment_question if payload else None

    def work() -> ReassessmentOut:
        try:
            return asyncio.run(run_agent_check(db, company, llm, agent, question))
        except AnalysisError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except AgentError as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"Agent failure: {exc}") from exc
        except LLMError as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"LLM failure: {exc}") from exc

    return stream_json(work)
