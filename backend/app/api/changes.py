from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Company
from ..schemas import ChangeEntry
from ..services.changes import build_timeline
from .deps import get_company

router = APIRouter(tags=["changes"])


@router.get("/companies/{company_id}/changes", response_model=list[ChangeEntry])
def changes(company: Company = Depends(get_company), db: Session = Depends(get_db)) -> list[ChangeEntry]:
    return build_timeline(db, company)
