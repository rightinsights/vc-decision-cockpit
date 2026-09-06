from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models import Company, Document, MonitoringEvent
from ..pdf import extract_pages, validate_pdf_bytes
from ..schemas import CompanyCreate, CompanyOut, DocumentOut, PipelineRow
from ..services.analysis import latest_assessment, latest_decision, latest_document
from .deps import get_company

router = APIRouter(tags=["companies"])


@router.post("/companies", response_model=CompanyOut, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> Company:
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/companies", response_model=list[PipelineRow])
def list_companies(db: Session = Depends(get_db)) -> list[PipelineRow]:
    rows: list[PipelineRow] = []
    for company in db.execute(select(Company).order_by(Company.created_at.desc())).scalars().all():
        assessment = latest_assessment(db, company.id)
        decision = latest_decision(db, company.id)
        document = latest_document(db, company.id)
        last_event = db.execute(
            select(MonitoringEvent).where(MonitoringEvent.company_id == company.id)
            .order_by(MonitoringEvent.created_at.desc())
        ).scalars().first()
        stamps = [company.updated_at] + [x.created_at for x in (assessment, decision, document, last_event) if x]
        rows.append(PipelineRow(
            **CompanyOut.model_validate(company).model_dump(),
            has_deck=document is not None,
            has_analysis=assessment is not None,
            recommendation=assessment.recommendation if assessment else None,
            overall_score=assessment.overall_score if assessment else None,
            decision=decision.decision if decision else None,
            main_concern=assessment.main_concern if assessment else None,
            last_changed=max(stamps),
        ))
    return rows


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company_detail(company: Company = Depends(get_company)) -> Company:
    return company


@router.post("/companies/{company_id}/deck", response_model=DocumentOut, status_code=201)
async def upload_deck(
    file: UploadFile,
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Document:
    data = await file.read()
    try:
        validate_pdf_bytes(data, settings.max_upload_mb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", file.filename or "deck.pdf")[:120] or "deck.pdf"
    target_dir = settings.resolved_upload_dir() / company.id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid.uuid4().hex}.pdf"
    target.write_bytes(data)
    try:
        pages = extract_pages(str(target), settings.max_pages)
    except Exception as exc:  # corrupt PDF, too many pages, parser failure
        Path(target).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc

    document = Document(
        company_id=company.id,
        file_name=safe_name,
        file_path=str(target),
        page_count=len(pages),
        extracted_text="\n\n".join(p["text"] for p in pages),
        pages_json=pages,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
