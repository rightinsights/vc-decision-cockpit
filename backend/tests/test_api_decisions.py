from app.llm_schemas import AssessmentOutput, DeckExtraction
from tests.conftest import canned_assessment, canned_extraction, create_company_with_deck, install_fake_llm


def test_decision_requires_rationale(client):
    company = client.post("/companies", json={"name": "Acme"}).json()
    res = client.post(f"/companies/{company['id']}/decisions", json={"decision": "WATCH", "rationale": "  "})
    assert res.status_code == 422
    res = client.post(f"/companies/{company['id']}/decisions", json={"decision": "INVEST", "rationale": "nope"})
    assert res.status_code == 422


def test_decisions_append_only_and_linked_to_latest_assessment(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment()})
    company = create_company_with_deck(client, deck_pdf)
    assessment_id = client.post(f"/companies/{company['id']}/analyze").json()["assessment"]["id"]

    first = client.post(f"/companies/{company['id']}/decisions",
                        json={"decision": "WATCH", "rationale": "Founder fit strong, no customer proof"})
    assert first.status_code == 201, first.text
    assert first.json()["assessment_id"] == assessment_id

    second = client.post(f"/companies/{company['id']}/decisions",
                         json={"decision": "DILIGENCE", "rationale": "Pilots confirmed paid"})
    assert second.status_code == 201

    history = client.get(f"/companies/{company['id']}/decisions").json()
    assert [d["decision"] for d in history] == ["DILIGENCE", "WATCH"]  # latest first, old one still visible

    analysis = client.get(f"/companies/{company['id']}/analysis").json()
    assert analysis["decision"]["decision"] == "DILIGENCE"
    assert client.get("/companies").json()[0]["decision"] == "DILIGENCE"
