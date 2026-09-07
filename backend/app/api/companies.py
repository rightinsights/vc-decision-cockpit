from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..llm import LLMClient, LLMError, get_llm
from ..models import Company, Document, MonitoringEvent
from ..ocr import transcribe_image_pages
from ..pdf import extract_pages, validate_pdf_bytes
from ..schemas import CompanyCreate, CompanyOut, DocumentOut, PipelineRow
from ..services.analysis import latest_assessment, latest_decision, latest_document
from .deps import get_company
from .longrun import stream_json

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


@router.delete("/companies/{company_id}", status_code=204)
def delete_company(
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """Hard delete: every row for the company (cascade) and its uploaded files."""
    upload_dir = settings.resolved_upload_dir() / company.id
    db.delete(company)
    db.commit()
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)


@router.post("/companies/{company_id}/deck", response_model=DocumentOut)
async def upload_deck(
    file: UploadFile,
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMClient = Depends(get_llm),
) -> StreamingResponse:
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

    def work() -> DocumentOut:
        try:
            final_pages, ocr_count = transcribe_image_pages(str(target), pages, llm)
        except LLMError as exc:
            Path(target).unlink(missing_ok=True)
            raise HTTPException(status_code=502, detail=f"Could not transcribe image-only pages: {exc}") from exc
        if not any((p.get("text") or "").strip() for p in final_pages):
            Path(target).unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="No readable text on any page, even after transcription.")
        document = Document(
            company_id=company.id,
            file_name=safe_name,
            file_path=str(target),
            page_count=len(final_pages),
            ocr_pages=ocr_count,
            extracted_text="\n\n".join(p["text"] for p in final_pages),
            pages_json=final_pages,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return DocumentOut.model_validate(document)

    return stream_json(work)
