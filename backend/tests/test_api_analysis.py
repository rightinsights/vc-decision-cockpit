from app.llm_schemas import AssessmentOutput, DeckExtraction, QuestionSet
from tests.conftest import (
    CANNED_SCORES, canned_assessment, canned_extraction, canned_questions,
    create_company_with_deck, install_fake_llm,
)


def test_analyze_requires_deck(client):
    install_fake_llm({})
    company = client.post("/companies", json={"name": "NoDeck"}).json()
    res = client.post(f"/companies/{company['id']}/analyze")
    assert res.status_code == 400
    assert "Upload a pitch deck" in res.json()["detail"]


def test_analyze_persists_snapshot_claims_evidence_and_python_scored_assessment(client, deck_pdf):
    fake = install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment()})
    company = create_company_with_deck(client, deck_pdf)

    res = client.post(f"/companies/{company['id']}/analyze")
    assert res.status_code == 200, res.text
    body = res.json()

    # prompt received the page-marked deck text and the company hint
    extraction_call = next(v for name, v in fake.calls if name == "extraction")
    assert "=== PAGE 3 ===" in extraction_call["deck_text"]
    assert "Acme Inspect" in extraction_call["company_hint"]

    assert body["snapshot"]["problem"] == "Inspectors re-key weld data manually"
    assert body["company"]["stage"] == "seed"  # filled from extraction because user left it blank

    claims = body["claims"]
    assert [c["source_page"] for c in claims] == [2, 3]
    pilots = next(c for c in claims if c["category"] == "traction")
    assert pilots["missing_proof"] == "Signed pilot agreements and invoices"
    assert len(pilots["evidence"]) == 1
    assert pilots["evidence"][0]["relation"] == "SUPPORTS"
    assert pilots["evidence"][0]["source_type"] == "DECK"
    assert pilots["evidence"][0]["source_page"] == 3

    assessment = body["assessment"]
    # Python computes: sum(((s-1)/4)*w) = 57.5 -> 58, band WATCH
    assert assessment["overall_score"] == 58
    assert assessment["recommendation"] == "WATCH"
    assert assessment["used_weight"] == 100
    assert assessment["trigger"] == "DECK"
    assert assessment["criterion_scores"]["customer_evidence"]["score"] == 2
    assert assessment["main_concern"] == "No proof the pilots are paid."
    assert body["decision"] is None
    assert body["questions"] == []

    pipeline = client.get("/companies").json()[0]
    assert pipeline["recommendation"] == "WATCH" and pipeline["overall_score"] == 58
    assert pipeline["main_concern"] == "No proof the pilots are paid."


def test_reanalyze_replaces_deck_claims_and_appends_assessment(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment()})
    company = create_company_with_deck(client, deck_pdf)
    client.post(f"/companies/{company['id']}/analyze")
    second = client.post(f"/companies/{company['id']}/analyze").json()
    assert len(second["claims"]) == 2  # replaced, not duplicated
    assert len(second["claims"][0]["evidence"]) == 1


def test_null_criterion_rescales(client, deck_pdf):
    scores = dict(CANNED_SCORES)
    scores["customer_evidence"] = None
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment(scores)})
    company = create_company_with_deck(client, deck_pdf)
    assessment = client.post(f"/companies/{company['id']}/analyze").json()["assessment"]
    assert assessment["used_weight"] == 90
    # remaining weighted = 57.5 - 2.5 = 55 over 90 -> 61.1 -> 61
    assert assessment["overall_score"] == 61
    assert assessment["criterion_scores"]["customer_evidence"]["score"] is None


def test_llm_failure_returns_502_and_persists_nothing(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction()})  # no AssessmentOutput -> FakeLLM raises
    company = create_company_with_deck(client, deck_pdf)
    res = client.post(f"/companies/{company['id']}/analyze")
    assert res.status_code == 502
    analysis = client.get(f"/companies/{company['id']}/analysis").json()
    assert analysis["assessment"] is None
    assert analysis["claims"] == []


def test_questions_require_analysis_first(client, deck_pdf):
    install_fake_llm({QuestionSet: canned_questions()})
    company = create_company_with_deck(client, deck_pdf)
    res = client.post(f"/companies/{company['id']}/meeting-questions")
    assert res.status_code == 400


def test_exactly_five_questions_enforced_with_one_retry(client, deck_pdf):
    fake = install_fake_llm({
        DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment(),
        QuestionSet: [canned_questions(4), canned_questions(4)],
    })
    company = create_company_with_deck(client, deck_pdf)
    client.post(f"/companies/{company['id']}/analyze")
    res = client.post(f"/companies/{company['id']}/meeting-questions")
    assert res.status_code == 502
    assert "exactly 5" in res.json()["detail"]
    retry_call = [v for name, v in fake.calls if name == "questions"][1]
    assert "previous response contained 4" in retry_call["feedback"]


def test_five_questions_persist_with_positions(client, deck_pdf):
    install_fake_llm({
        DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment(),
        QuestionSet: [canned_questions(6), canned_questions(5)],
    })
    company = create_company_with_deck(client, deck_pdf)
    client.post(f"/companies/{company['id']}/analyze")
    res = client.post(f"/companies/{company['id']}/meeting-questions")
    assert res.status_code == 200, res.text
    assert [q["position"] for q in res.json()] == [1, 2, 3, 4, 5]
    analysis = client.get(f"/companies/{company['id']}/analysis").json()
    assert len(analysis["questions"]) == 5
    assert analysis["questions"][0]["question"] == "Q1?"
