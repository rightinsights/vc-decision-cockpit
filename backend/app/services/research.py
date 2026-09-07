"""
Public research, the first step for any company: Brave results -> one structured OpenAI call ->
sourced facts as WEB evidence -> profile snapshot (if no deck yet) -> thesis fit (initial or rescore).
"""

from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import thesis as T
from ..llm import LLMClient
from ..llm_schemas import ResearchReport, ResearchSnapshot
from ..models import Company, Evidence, ResearchRun
from ..schemas import ReassessmentOut, ResearchFactView, ResearchOut
from .analysis import claims_block, company_claims, latest_assessment, match_claim_id, run_assessment, short_label
from .brave import BraveClient, build_queries, domain_of, gather_results, normalize_url
from .reassess import build_reassessment

DEFAULT_BRIEF = (
    "Assess this company against the thesis from public sources: who the founders are and whether they have firsthand "
    "experience of the workflow; what expensive, manual, or expert-heavy workflow the product automates and for whom; "
    "who buys it; evidence of paying customers, pilots, or revenue; proprietary data, integrations, or other defensibility; "
    "sector, stage, geography, funding, competitors, and material risks."
)


def latest_research(db: Session, company_id: str) -> ResearchRun | None:
    stmt = select(ResearchRun).where(ResearchRun.company_id == company_id).order_by(ResearchRun.created_at.desc())
    return db.execute(stmt).scalars().first()


def research_view(run: ResearchRun, reassessment: ReassessmentOut | None = None) -> ResearchOut:
    report = run.report_json or {}
    domains = Counter(domain_of(r.get("url")) for r in run.results_json or [])
    return ResearchOut(
        id=run.id,
        brief=run.brief,
        snapshot_applied=bool(report.get("snapshot_applied")),
        initial_assessment=bool(report.get("initial_assessment")),
        queries=list(run.queries_json or []),
        result_count=len(run.results_json or []),
        domain_count=len([d for d in domains if d]),
        facts_kept=run.facts_kept,
        facts_dropped=run.facts_dropped,
        search_provider=run.search_provider,
        summary=report.get("summary", ""),
        entity_note=report.get("entity_note"),
        facts=[ResearchFactView(**f) for f in report.get("facts", [])],
        unknowns=list(report.get("unknowns", [])),
        created_at=run.created_at,
        reassessment=reassessment,
    )


def apply_web_snapshot(company: Company, snap: ResearchSnapshot) -> bool:
    """Fill the profile from public sources when there is no deck yet. Deck extraction later overrides non-null fields."""
    if company.snapshot_json and company.snapshot_json.get("source") != "web":
        return False  # a deck already populated the profile
    values = {
        "company_name": company.name,
        "founders": [f.model_dump() for f in snap.founders],
        "problem": snap.problem,
        "workflow": snap.workflow,
        "customer": snap.customer,
        "buyer": snap.buyer,
        "solution": snap.solution,
        "business_model": snap.business_model,
        "traction": snap.traction,
        "funding_ask": snap.funding_ask,
        "unknowns": [],
        "source": "web",
    }
    if not any(v for k, v in values.items() if k not in ("company_name", "founders", "traction", "unknowns", "source")) and not snap.founders and not snap.traction:
        return False
    company.snapshot_json = values
    company.stage = company.stage or short_label(snap.stage)
    company.geography = company.geography or short_label(snap.geography, 60)
    return True


async def run_research(db: Session, company: Company, llm: LLMClient, brave: BraveClient, brief: str | None) -> ResearchOut:
    brief = (brief or "").strip() or DEFAULT_BRIEF
    queries = build_queries(company.name, company.website, brief)
    results = await gather_results(brave, queries)

    report = llm.parse(
        "research",
        {
            "thesis_text": T.THESIS_TEXT,
            "positive_signals": "\n".join(f"- {s}" for s in T.POSITIVE_SIGNALS),
            "out_of_scope": "\n".join(f"- {s}" for s in T.OUT_OF_SCOPE),
            "company_name": company.name,
            "website": company.website or "unknown",
            "stage_geography": ", ".join(x for x in (company.stage, company.geography) if x) or "unknown",
            "brief": brief,
            "claims_block": claims_block(db, company.id),
            "results_json": json.dumps(
                [{"title": r["title"], "url": r["url"], "snippet": r["description"], "age": r["age"]} for r in results],
                ensure_ascii=False, indent=1,
            ),
        },
        ResearchReport,
    )

    # Provenance gate: a fact may only cite a URL Brave actually returned.
    allowed = {normalize_url(r["url"]): r["url"] for r in results}
    valid_claim_ids = {c.id for c in company_claims(db, company.id)}
    kept, dropped = [], 0
    for fact in report.facts:
        canonical = allowed.get(normalize_url(fact.source_url))
        if canonical is None:
            dropped += 1
            continue
        fact.source_url = canonical
        if fact.claim_id and fact.claim_id not in valid_claim_ids:
            fact.claim_id = None
            fact.relation = None
        kept.append(fact)

    snapshot_applied = apply_web_snapshot(company, report.snapshot)
    before = latest_assessment(db, company.id)

    run = ResearchRun(
        company_id=company.id,
        brief=brief,
        queries_json=queries,
        results_json=list(results),
        report_json={
            "summary": report.summary,
            "entity_note": report.entity_note,
            "unknowns": report.unknowns,
            "facts": [f.model_dump() for f in kept],
            "snapshot_applied": snapshot_applied,
            "initial_assessment": before is None,
        },
        facts_kept=len(kept),
        facts_dropped=dropped,
        search_provider=getattr(brave, "name", "brave"),
    )
    db.add(run)
    db.flush()

    new_evidence: list[Evidence] = []
    for fact in kept:
        claim_id = fact.claim_id or match_claim_id(db, company.id, fact.finding)
        row = Evidence(
            company_id=company.id,
            claim_id=claim_id,
            evidence_text=fact.finding,
            relation=fact.relation or ("QUALIFIES" if claim_id else "SUPPORTS"),
            source_url=fact.source_url,
            source_type="WEB",
            source_ref_id=run.id,
        )
        db.add(row)
        new_evidence.append(row)
    db.flush()

    reassessment: ReassessmentOut | None = None
    if kept or before is None:
        lines = [f"PUBLIC RESEARCH ({run.created_at.date().isoformat()}, Brave + OpenAI): {report.summary}"]
        for fact in kept:
            lines.append(f"- [{fact.category}, {fact.confidence}] {fact.finding} (source: {fact.source_url})")
        after = run_assessment(db, company, llm, trigger="RESEARCH", source_ref_id=run.id, extra_context="\n".join(lines))
        db.commit()
        for row in new_evidence:
            db.refresh(row)
        reassessment = build_reassessment(
            db, company, trigger="RESEARCH", before=before, after=after, event=None,
            note_summary=report.summary, new_evidence=new_evidence,
        )
    else:
        db.commit()
    db.refresh(run)
    return research_view(run, reassessment)
