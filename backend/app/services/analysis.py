"""Deck -> extraction -> claims/evidence -> assessment. Shared assessment runner for reassessments."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import thesis as T
from ..llm import LLMClient
from ..llm_schemas import AssessmentOutput, DeckExtraction, normalize_criteria
from ..models import Assessment, Claim, Company, Decision, DiligenceQuestion, Document, Evidence, MonitoringEvent
from ..pdf import pages_to_prompt_text
from ..schemas import (
    AnalysisOut, AssessmentOut, ClaimOut, CompanyOut, DecisionOut, DocumentOut,
    MonitoringEventOut, QuestionOut, ThesisOut,
)
from ..scoring import compute_overall, recommend
from ..seed import get_thesis


class AnalysisError(ValueError):
    pass


# ---- lookups ----

def latest_document(db: Session, company_id: str) -> Document | None:
    stmt = select(Document).where(Document.company_id == company_id).order_by(Document.created_at.desc())
    return db.execute(stmt).scalars().first()


def latest_assessment(db: Session, company_id: str) -> Assessment | None:
    stmt = select(Assessment).where(Assessment.company_id == company_id).order_by(Assessment.created_at.desc())
    return db.execute(stmt).scalars().first()


def latest_decision(db: Session, company_id: str) -> Decision | None:
    stmt = select(Decision).where(Decision.company_id == company_id).order_by(Decision.created_at.desc())
    return db.execute(stmt).scalars().first()


def company_claims(db: Session, company_id: str) -> list[Claim]:
    stmt = select(Claim).where(Claim.company_id == company_id).order_by(Claim.source_page.nulls_last(), Claim.created_at)
    return list(db.execute(stmt).scalars().all())


def unlinked_evidence(db: Session, company_id: str) -> list[Evidence]:
    stmt = select(Evidence).where(Evidence.company_id == company_id, Evidence.claim_id.is_(None)).order_by(Evidence.created_at)
    return list(db.execute(stmt).scalars().all())


# ---- prompt blocks ----

def snapshot_json(company: Company) -> str:
    snap = dict(company.snapshot_json or {})
    snap.update({"name": company.name, "website": company.website, "stage": company.stage, "geography": company.geography})
    return json.dumps(snap, indent=2, ensure_ascii=False)


def claims_block(db: Session, company_id: str) -> str:
    lines: list[str] = []
    for claim in company_claims(db, company_id):
        page = f"p{claim.source_page}" if claim.source_page else "no page"
        lines.append(f"- CLAIM [{claim.id}] ({claim.category}, {page}, strength {claim.evidence_strength}): {claim.claim_text}")
        if claim.missing_proof:
            lines.append(f"    missing proof: {claim.missing_proof}")
        for ev in claim.evidence:
            where = f"p{ev.source_page}" if ev.source_page else (ev.source_url or ev.source_type)
            lines.append(f"    EVIDENCE [ev:{ev.id}] {ev.relation} via {ev.source_type} ({where}): {ev.evidence_text}")
    loose = unlinked_evidence(db, company_id)
    if loose:
        lines.append("- EVIDENCE NOT TIED TO A SPECIFIC CLAIM:")
        for ev in loose:
            where = ev.source_url or ev.source_type
            lines.append(f"    EVIDENCE [ev:{ev.id}] {ev.relation} via {ev.source_type} ({where}): {ev.evidence_text}")
    return "\n".join(lines) if lines else "(no claims extracted)"


def criteria_block() -> str:
    return "\n".join(f"- {c['key']} (weight {c['weight']}): {c['description']}" for c in T.CRITERIA)


# ---- extraction ----

def apply_extraction(company: Company, extraction: DeckExtraction) -> None:
    company.name = company.name or extraction.company_name or company.name
    company.website = company.website or extraction.website
    company.stage = company.stage or extraction.stage
    company.geography = company.geography or extraction.geography
    company.snapshot_json = {
        "company_name": extraction.company_name,
        "founders": [f.model_dump() for f in extraction.founders],
        "problem": extraction.problem,
        "workflow": extraction.workflow,
        "customer": extraction.customer,
        "buyer": extraction.buyer,
        "solution": extraction.solution,
        "business_model": extraction.business_model,
        "traction": extraction.traction,
        "funding_ask": extraction.funding_ask,
        "unknowns": extraction.unknowns,
    }


def replace_deck_claims(db: Session, company: Company, document: Document, extraction: DeckExtraction) -> list[Claim]:
    """Re-analysis replaces deck-derived claims and their deck evidence; keeps agent/note evidence."""
    for claim in company_claims(db, company.id):
        db.delete(claim)  # cascades to its evidence rows
    db.flush()
    created: list[Claim] = []
    for item in extraction.claims:
        claim = Claim(
            company_id=company.id,
            document_id=document.id,
            claim_text=item.claim,
            category=item.category,
            source_page=item.source_page,
            supporting_text=item.supporting_text,
            evidence_strength=item.evidence_strength,
            missing_proof=item.missing_proof,
        )
        db.add(claim)
        db.flush()
        if item.supporting_text:
            db.add(Evidence(
                company_id=company.id, claim_id=claim.id, evidence_text=item.supporting_text,
                relation="SUPPORTS", source_page=item.source_page, source_type="DECK", source_ref_id=document.id,
            ))
        created.append(claim)
    db.flush()
    return created


# ---- assessment ----

def run_assessment(
    db: Session, company: Company, llm: LLMClient, *, trigger: str, source_ref_id: str | None, extra_context: str | None,
) -> Assessment:
    thesis = get_thesis(db)
    output = llm.parse(
        "assessment",
        {
            "thesis_text": T.THESIS_TEXT,
            "positive_signals": "\n".join(f"- {s}" for s in T.POSITIVE_SIGNALS),
            "out_of_scope": "\n".join(f"- {s}" for s in T.OUT_OF_SCOPE),
            "criteria": criteria_block(),
            "snapshot": snapshot_json(company),
            "claims_block": claims_block(db, company.id),
            "extra_context": extra_context or "none",
        },
        AssessmentOutput,
    )
    scores = normalize_criteria(output)
    result = compute_overall({k: v["score"] for k, v in scores.items()})
    assessment = Assessment(
        company_id=company.id,
        thesis_id=thesis.id,
        trigger=trigger,
        source_ref_id=source_ref_id,
        criterion_scores_json=scores,
        overall_score=result["overall"],
        used_weight=result["used_weight"],
        recommendation=recommend(result["overall"]),
        summary=output.summary,
        main_concern=output.main_concern,
    )
    db.add(assessment)
    db.flush()
    return assessment


def analyze_company(db: Session, company: Company, llm: LLMClient) -> Assessment:
    document = latest_document(db, company.id)
    if document is None:
        raise AnalysisError("Upload a pitch deck before running analysis.")
    pages = document.pages_json or []
    extraction = llm.parse(
        "extraction",
        {
            "company_hint": f"{company.name} ({company.website or 'no website given'})",
            "page_count": str(len(pages)),
            "deck_text": pages_to_prompt_text(pages),
        },
        DeckExtraction,
    )
    apply_extraction(company, extraction)
    replace_deck_claims(db, company, document, extraction)
    assessment = run_assessment(db, company, llm, trigger="DECK", source_ref_id=document.id, extra_context=None)
    db.commit()
    db.refresh(company)
    return assessment


# ---- read model ----

def build_analysis(db: Session, company: Company) -> AnalysisOut:
    thesis = get_thesis(db)
    assessment = latest_assessment(db, company.id)
    questions: list[DiligenceQuestion] = []
    if assessment is not None:
        stmt = (
            select(DiligenceQuestion)
            .where(DiligenceQuestion.company_id == company.id)
            .order_by(DiligenceQuestion.created_at.desc(), DiligenceQuestion.position)
        )
        rows = list(db.execute(stmt).scalars().all())
        if rows:
            newest_batch = rows[0].assessment_id
            questions = sorted([q for q in rows if q.assessment_id == newest_batch], key=lambda q: q.position)
    events = list(db.execute(
        select(MonitoringEvent).where(MonitoringEvent.company_id == company.id).order_by(MonitoringEvent.created_at.desc())
    ).scalars().all())
    document = latest_document(db, company.id)
    decision = latest_decision(db, company.id)
    criteria_meta: dict[str, Any] = thesis.criteria_json or {}
    from .research import latest_research, research_view  # local import: research imports this module

    research_run = latest_research(db, company.id)
    return AnalysisOut(
        research=research_view(research_run) if research_run else None,
        company=CompanyOut.model_validate(company),
        snapshot=company.snapshot_json,
        document=DocumentOut.model_validate(document) if document else None,
        claims=[ClaimOut.model_validate(c) for c in company_claims(db, company.id)],
        assessment=AssessmentOut.model_validate(assessment) if assessment else None,
        questions=[QuestionOut.model_validate(q) for q in questions],
        decision=DecisionOut.model_validate(decision) if decision else None,
        thesis=ThesisOut(
            id=thesis.id, name=thesis.name, thesis_text=thesis.thesis_text,
            criteria=criteria_meta.get("criteria", T.CRITERIA),
            positive_signals=criteria_meta.get("positive_signals", T.POSITIVE_SIGNALS),
            out_of_scope=criteria_meta.get("out_of_scope", T.OUT_OF_SCOPE),
        ),
        monitoring_events=[MonitoringEventOut.model_validate(e) for e in events],
    )
