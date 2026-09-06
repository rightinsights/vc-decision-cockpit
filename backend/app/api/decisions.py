from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company
from ..schemas import DecisionCreate, DecisionOut
from ..services.decisions import list_decisions, record_decision
from .deps import get_company

router = APIRouter(tags=["decisions"])


@router.post("/companies/{company_id}/decisions", response_model=DecisionOut, status_code=201)
def create_decision(
    payload: DecisionCreate, company: Company = Depends(get_company), db: Session = Depends(get_db)
) -> DecisionOut:
    return DecisionOut.model_validate(record_decision(db, company, payload))


@router.get("/companies/{company_id}/decisions", response_model=list[DecisionOut])
def get_decisions(company: Company = Depends(get_company), db: Session = Depends(get_db)) -> list[DecisionOut]:
    return [DecisionOut.model_validate(d) for d in list_decisions(db, company.id)]
