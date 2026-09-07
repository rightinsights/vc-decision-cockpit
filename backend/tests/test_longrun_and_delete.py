import json

from app.llm_schemas import AssessmentOutput, DeckExtraction, QuestionSet
from tests.conftest import canned_assessment, canned_extraction, canned_questions, create_company_with_deck, install_fake_llm


def test_long_endpoints_stream_valid_json_bodies(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: [canned_assessment(), canned_assessment()], QuestionSet: canned_questions()})
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    res = client.post(f"/companies/{cid}/analyze")
    assert res.status_code == 200 and res.headers["content-type"].startswith("application/json")
    body = json.loads(res.text)  # leading keepalive whitespace, if any, must not break parsing
    assert body["assessment"]["overall_score"] == 58

    res = client.post(f"/companies/{cid}/meeting-questions")
    assert res.status_code == 200 and len(res.json()) == 5

    client.post(f"/companies/{cid}/decisions", json={"decision": "WATCH", "rationale": "watching for customer proof"})
    res = client.post(f"/companies/{cid}/agent-check", json={})
    assert res.status_code == 200 and res.json()["event"]["event_found"] is True


def test_long_endpoint_errors_arrive_inside_the_stream(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction()})  # no assessment canned -> LLM failure mid-way
    company = create_company_with_deck(client, deck_pdf)
    res = client.post(f"/companies/{company['id']}/analyze")
    assert res.status_code == 200  # status already sent; the error is in the body
    body = res.json()
    assert body["status"] == 502 and "LLM failure" in body["detail"]

    res = client.post(f"/companies/{company['id']}/agent-check", json={})
    assert res.json()["status"] == 400 and "Run the deck analysis" in res.json()["detail"]


def test_reanalysis_keeps_agent_evidence(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: [canned_assessment()] * 4})
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    client.post(f"/companies/{cid}/analyze")
    client.post(f"/companies/{cid}/decisions", json={"decision": "WATCH", "rationale": "watching for customer proof"})
    client.post(f"/companies/{cid}/agent-check", json={})
    before = client.get(f"/companies/{cid}/analysis").json()
    assert sum(1 for c in before["claims"] for e in c["evidence"] if e["source_type"] == "AGENT") == 1

    client.post(f"/companies/{cid}/analyze")  # re-analysis replaces deck claims
    after = client.get(f"/companies/{cid}/analysis").json()
    agent_rows = [e for c in after["claims"] for e in c["evidence"] if e["source_type"] == "AGENT"]
    assert len(agent_rows) == 1, "agent evidence must survive re-analysis and re-link to the new claim"
    assert len(after["claims"]) == 2


def test_delete_company_removes_rows_and_files(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment()})
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    client.post(f"/companies/{cid}/analyze")
    assert client.delete(f"/companies/{cid}").status_code == 204
    assert client.get(f"/companies/{cid}").status_code == 404
    assert client.get("/companies").json() == []
    assert client.delete(f"/companies/{cid}").status_code == 404
