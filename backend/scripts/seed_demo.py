"""
Dev-only: insert one clearly labelled sample company with canned claims, evidence, assessment,
questions and a decision so the UI can be reviewed without an LLM call.

    python -m scripts.seed_demo          # adds "Sample: Acme Inspect"
    python -m scripts.seed_demo --remove # deletes it
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.models import Assessment, Claim, Company, Decision, DiligenceQuestion, Document, Evidence
from app.pdf import extract_pages
from app.scoring import compute_overall, recommend
from app.seed import seed_thesis
from app.thesis import CRITERION_KEYS

NAME = "Sample: Acme Inspect"

PAGES = [
    "Acme Inspect. AI-drafted weld inspection reports for pipeline operators.",
    "Problem: certified inspectors spend about 6 hours per report re-keying field data into legacy forms.",
    "Traction: two paid pilots with regional gas utilities. Pipots started in Q2.",
    "Team: CEO Jane Doe spent 12 years as an API 1104 certified weld inspector. CTO built inspection software at a major EPC.",
    "Business model: per-inspector annual licence, $4,800 per seat. Ask: $1.5M seed.",
]

CLAIMS = [
    ("Two paid pilots with regional gas utilities", "traction", 3, "two paid pilots with regional gas utilities", "MEDIUM",
     "Signed pilot agreements, invoices, and pilot success criteria"),
    ("Inspectors spend about 6 hours per report re-keying data", "roi", 2, "spend about 6 hours per report re-keying field data", "LOW",
     "Time study across at least five inspectors, before and after"),
    ("CEO has 12 years as a certified weld inspector", "team", 4, "12 years as an API 1104 certified weld inspector", "MEDIUM",
     "Certification record and reference calls with former employers"),
    ("Per-inspector licence at $4,800 per seat", "business_model", 5, "$4,800 per seat", "LOW",
     "Any customer that has actually paid the list price"),
]

SCORES = {
    "founder_domain_fit": 4, "workflow_pain": 4, "workflow_frequency": 3, "buyer_clarity": 3,
    "customer_evidence": 2, "roi_clarity": 3, "defensibility": 2, "scalability": 3, "stage_geography_fit": 5,
}
REASONS = {
    "founder_domain_fit": "CEO's 12 years as a certified inspector is firsthand workflow knowledge (p4).",
    "workflow_pain": "Six hours of re-keying per report is a concrete, expensive manual step (p2).",
    "workflow_frequency": "Reports are produced per inspection; frequency is implied, not quantified (p2).",
    "buyer_clarity": "Pipeline operators named as customers; buyer role not identified (p1, p3).",
    "customer_evidence": "Two pilots described as paid, no contract or revenue evidence (p3).",
    "roi_clarity": "Time saving asserted without a before/after measurement (p2).",
    "defensibility": "No proprietary data or integration moat described; report drafting could be replicated.",
    "scalability": "Per-seat licence suggests software margins; deployment effort unknown (p5).",
    "stage_geography_fit": "Seed, United States (p5).",
}

QUESTIONS = [
    ("Are both pilots paying today, and what are the contract values and success criteria?",
     "Turns 'two paid pilots' from a claim into customer evidence and moves customer evidence from 2 to 3 or 4.",
     "Signed agreements with dollar amounts and a written conversion path to an annual licence.",
     "Free or heavily discounted pilots with no agreed success criteria.", "Two paid pilots with regional gas utilities"),
    ("How was the 6-hour figure measured, and across how many inspectors?",
     "The entire ROI story rests on it; a measured number changes ROI clarity, an anecdote does not.",
     "A time study with several inspectors and a before/after comparison on real reports.",
     "One inspector's estimate or the founder's own experience only.", "roi_clarity"),
    ("Who signs the purchase order at a utility, and what budget does it come from?",
     "Buyer clarity is scored 3 because no buyer role is named; a named budget owner resolves it.",
     "A specific role (head of integrity engineering) with an existing budget line for inspection tooling.",
     "'The operations team' with no owner or budget identified.", "buyer_clarity"),
    ("What data or workflow position would make this hard to replace with a general model in two years?",
     "Defensibility is the lowest-scored weighted criterion; the answer decides whether this is a feature or a company.",
     "Accumulated labelled inspection data, integration into the operator's system of record, or regulatory audit trail.",
     "'Our prompts are better' or reliance on public models with no proprietary data.", "defensibility"),
    ("How many hours of implementation and training does each new utility require?",
     "Services-heavy rollout would cut scalability and undermine the per-seat pricing model.",
     "Under two weeks with no on-site work, driven by a standard field-form import.",
     "Custom integration per customer measured in months.", "scalability"),
]


def remove(db) -> None:
    for row in db.execute(select(Company).where(Company.name == NAME)).scalars().all():
        db.delete(row)
    db.commit()
    print("removed sample company")


def seed(db) -> None:
    if db.execute(select(Company).where(Company.name == NAME)).scalars().first():
        print("sample company already present")
        return
    thesis = seed_thesis(db)
    company = Company(name=NAME, website="https://acmeinspect.example", stage="seed", geography="United States")
    db.add(company)
    db.flush()

    upload_dir = get_settings().resolved_upload_dir() / company.id
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / "sample-acme-inspect.pdf"
    doc = pymupdf.open()
    for text in PAGES:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=11)
    doc.save(str(pdf_path))
    doc.close()
    pages = extract_pages(str(pdf_path), 200)
    document = Document(company_id=company.id, file_name="sample-acme-inspect.pdf", file_path=str(pdf_path),
                        page_count=len(pages), extracted_text="\n\n".join(p["text"] for p in pages), pages_json=pages)
    db.add(document)
    db.flush()

    company.snapshot_json = {
        "company_name": "Acme Inspect",
        "founders": [{"name": "Jane Doe", "role": "CEO", "domain_background": "12 years as an API 1104 certified weld inspector"},
                     {"name": "Sam Lee", "role": "CTO", "domain_background": "Built inspection software at a major EPC"}],
        "problem": "Certified inspectors re-key field data into legacy report forms by hand.",
        "workflow": "Post-inspection weld report drafting and submission.",
        "customer": "Pipeline operators and gas utilities.",
        "buyer": None,
        "solution": "AI drafts the inspection report from field data and photos for inspector sign-off.",
        "business_model": "Per-inspector annual licence, $4,800 per seat.",
        "traction": ["Two paid pilots with regional gas utilities"],
        "funding_ask": "$1.5M seed",
        "unknowns": ["Buyer role and budget owner", "Pilot contract values", "Implementation effort per customer"],
    }

    for text, category, page, quote, strength, missing in CLAIMS:
        claim = Claim(company_id=company.id, document_id=document.id, claim_text=text, category=category,
                      source_page=page, supporting_text=quote, evidence_strength=strength, missing_proof=missing)
        db.add(claim)
        db.flush()
        db.add(Evidence(company_id=company.id, claim_id=claim.id, evidence_text=quote, relation="SUPPORTS",
                        source_page=page, source_type="DECK", source_ref_id=document.id))

    scores = {k: {"score": SCORES[k], "reason": REASONS[k], "evidence_refs": []} for k in CRITERION_KEYS}
    result = compute_overall(SCORES)
    assessment = Assessment(company_id=company.id, thesis_id=thesis.id, trigger="DECK", source_ref_id=document.id,
                            criterion_scores_json=scores, overall_score=result["overall"], used_weight=result["used_weight"],
                            recommendation=recommend(result["overall"]),
                            summary="Strong founder and workflow fit. Customer and ROI evidence are founder claims so far.",
                            main_concern="No proof that the two pilots are paying or will convert to licences.")
    db.add(assessment)
    db.flush()

    for position, (q, why, strong, weak, basis) in enumerate(QUESTIONS, start=1):
        db.add(DiligenceQuestion(company_id=company.id, assessment_id=assessment.id, position=position, question=q,
                                 why_it_matters=why, strong_answer=strong, weak_answer=weak, basis=basis))

    db.add(Decision(company_id=company.id, assessment_id=assessment.id, decision="WATCH",
                    rationale="Founder fit is real. No customer proof yet; revisit when pilot contracts are visible."))
    db.commit()
    print(f"seeded {NAME} ({company.id}) score={result['overall']} recommendation={recommend(result['overall'])}")


if __name__ == "__main__":
    init_db()
    with SessionLocal() as session:
        remove(session) if "--remove" in sys.argv else seed(session)
