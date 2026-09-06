"""Test wiring: temp SQLite + uploads, FakeLLM injected via dependency override."""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="vcdc-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ["AGENT_PROVIDER"] = "mock"

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.llm import FakeLLM, get_llm  # noqa: E402
from app.llm_schemas import (  # noqa: E402
    AssessmentOutput, CriterionScore, DeckExtraction, DiligenceQuestionOut, ExtractedClaim,
    ExtractedFounder, QuestionSet,
)
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_llm, None)


@pytest.fixture
def deck_pdf(tmp_path) -> Path:
    doc = pymupdf.open()
    for text in [
        "Acme Inspect: AI for pipeline weld inspection reports",
        "Problem: inspectors spend 6 hours per report re-keying data",
        "Traction: two paid pilots with regional utilities",
        "Team: CEO spent 12 years as a certified weld inspector",
    ]:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    path = tmp_path / "acme.pdf"
    doc.save(str(path))
    doc.close()
    return path


# ---- canned LLM outputs ----

def canned_extraction() -> DeckExtraction:
    return DeckExtraction(
        company_name="Acme Inspect", website="https://acmeinspect.example", stage="seed", geography="United States",
        founders=[ExtractedFounder(name="Jane Doe", role="CEO", domain_background="12 years as certified weld inspector")],
        problem="Inspectors re-key weld data manually", workflow="Post-inspection report writing",
        customer="Pipeline operators", buyer="Head of integrity engineering", solution="AI report drafting from field data",
        business_model="Per-inspector SaaS", traction=["Two paid pilots"], funding_ask="$1.5M seed",
        claims=[
            ExtractedClaim(claim="Two paid pilots with regional utilities", category="traction", source_page=3,
                           supporting_text="two paid pilots with regional utilities", evidence_strength="MEDIUM",
                           missing_proof="Signed pilot agreements and invoices"),
            ExtractedClaim(claim="Inspectors spend 6 hours per report", category="roi", source_page=2,
                           supporting_text="inspectors spend 6 hours per report", evidence_strength="LOW",
                           missing_proof="Time study across several inspectors"),
        ],
        unknowns=["Pricing", "Pilot conversion timeline"],
    )


CANNED_SCORES = {
    "founder_domain_fit": 4, "workflow_pain": 4, "workflow_frequency": 3, "buyer_clarity": 3,
    "customer_evidence": 2, "roi_clarity": 3, "defensibility": 3, "scalability": 3, "stage_geography_fit": 5,
}


def canned_assessment(scores: dict | None = None, concern: str = "No proof the pilots are paid.") -> AssessmentOutput:
    scores = scores or CANNED_SCORES
    return AssessmentOutput(
        criteria=[CriterionScore(key=k, score=v, reason=f"reason for {k} (p2)", evidence_refs=["p2"]) for k, v in scores.items()],
        summary="Strong founder fit, thin customer evidence.",
        main_concern=concern,
    )


def canned_questions(count: int = 5) -> QuestionSet:
    return QuestionSet(questions=[
        DiligenceQuestionOut(question=f"Q{i}?", why_it_matters=f"why {i}", strong_answer=f"strong {i}",
                             weak_answer=f"weak {i}", basis="customer_evidence")
        for i in range(1, count + 1)
    ])


def install_fake_llm(responses: dict) -> FakeLLM:
    fake = FakeLLM(responses)
    app.dependency_overrides[get_llm] = lambda: fake
    return fake


def create_company_with_deck(client, deck_pdf, name="Acme Inspect"):
    company = client.post("/companies", json={"name": name, "website": "https://acmeinspect.example"}).json()
    with open(deck_pdf, "rb") as fh:
        upload = client.post(f"/companies/{company['id']}/deck", files={"file": ("acme.pdf", fh, "application/pdf")})
    assert upload.status_code == 201, upload.text
    return company
