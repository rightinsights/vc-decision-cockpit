import json

import httpx
import pytest

from app.agents.base import AgentError, AgentRequest, parse_finding
from app.agents.openclaw import OpenClawMonitoringAgent
from app.llm_schemas import AssessmentOutput, DeckExtraction
from tests.conftest import CANNED_SCORES, canned_assessment, canned_extraction, create_company_with_deck, install_fake_llm


def _after_scores():
    scores = dict(CANNED_SCORES)
    scores["customer_evidence"] = 4  # two paid contracts confirmed externally
    return scores


def test_agent_check_requires_watch_or_diligence(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment()})
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    assert client.post(f"/companies/{cid}/agent-check", json={}).status_code == 400  # no analysis
    client.post(f"/companies/{cid}/analyze")
    assert client.post(f"/companies/{cid}/agent-check", json={}).status_code == 400  # no decision
    client.post(f"/companies/{cid}/decisions", json={"decision": "PASS", "rationale": "out of scope"})
    res = client.post(f"/companies/{cid}/agent-check", json={})
    assert res.status_code == 400
    assert "WATCH or DILIGENCE" in res.json()["detail"]


def test_mock_agent_check_creates_event_evidence_and_reassessment(client, deck_pdf):
    fake = install_fake_llm({
        DeckExtraction: canned_extraction(),
        AssessmentOutput: [canned_assessment(), canned_assessment(_after_scores(), concern="Need contract values.")],
    })
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    client.post(f"/companies/{cid}/analyze")
    client.post(f"/companies/{cid}/decisions", json={"decision": "WATCH", "rationale": "No customer proof yet"})

    res = client.post(f"/companies/{cid}/agent-check", json={})
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["trigger"] == "AGENT"
    assert body["event"]["event_found"] is True
    assert body["event"]["source_url"].startswith("https://")
    assert body["event"]["agent_provider"] == "mock"
    assert "resolves this concern" in body["event"]["investment_question"]
    assert len(body["new_evidence"]) == 1
    assert body["new_evidence"][0]["source_type"] == "AGENT"
    assert body["new_evidence"][0]["source_url"] == body["event"]["source_url"]
    # open gap = weakest claim with missing proof (the LOW-strength ROI claim); agent evidence maps onto it
    assert "6 hours per report" in body["event"]["claim_or_gap_affected"]
    analysis = client.get(f"/companies/{cid}/analysis").json()
    roi = next(c for c in analysis["claims"] if c["category"] == "roi")
    assert any(e["source_type"] == "AGENT" for e in roi["evidence"])

    assert body["assessment_before"]["overall_score"] == 58
    assert body["assessment_after"]["overall_score"] == 63  # customer_evidence 2 -> 4 adds 5 points
    assert body["assessment_after"]["trigger"] == "AGENT"
    assert body["deltas"] == [{"key": "customer_evidence", "label": "Customer evidence", "old": 2, "new": 4,
                               "reason": "reason for customer_evidence (p2)"}]
    assert body["recommendation"] == {"before": "WATCH", "after": "WATCH", "changed": False}
    assert body["human_decision"]["decision"] == "WATCH"
    assert body["matters"] is True
    assert "remains WATCH" in body["explanation"]

    # the reassessment prompt saw the agent finding as new evidence
    second_assessment_call = [v for name, v in fake.calls if name == "assessment"][1]
    assert "AGENT FINDING" in second_assessment_call["extra_context"]
    assert "example.com" in second_assessment_call["claims_block"]

    # human decision untouched, assessment appended not replaced
    assert [d["decision"] for d in client.get(f"/companies/{cid}/decisions").json()] == ["WATCH"]
    assert analysis["assessment"]["id"] == body["assessment_after"]["id"]
    assert len(analysis["monitoring_events"]) == 1


def test_agent_check_accepts_custom_question(client, deck_pdf):
    fake = install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: [canned_assessment(), canned_assessment()]})
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    client.post(f"/companies/{cid}/analyze")
    client.post(f"/companies/{cid}/decisions", json={"decision": "DILIGENCE", "rationale": "worth a look"})
    res = client.post(f"/companies/{cid}/agent-check", json={"investment_question": "Are the pilots paying?"})
    assert res.status_code == 200
    assert res.json()["event"]["investment_question"] == "Are the pilots paying?"
    assert res.json()["deltas"] == []
    assert res.json()["matters"] is True  # mock suggests REVIEW
    assert len([v for name, v in fake.calls if name == "assessment"]) == 2


# ---- parse_finding ----

def test_parse_finding_accepts_fenced_bare_and_embedded_json():
    payload = {"event_found": True, "event_type": "customer", "summary": "s", "source_url": "https://x.y/z",
               "relevance": "r", "suggested_action": "REVIEW"}
    fenced = "Here is what I found:\n```json\n" + json.dumps(payload) + "\n```\nDone."
    assert parse_finding(fenced).event_type == "CUSTOMER"
    assert parse_finding(json.dumps(payload)).source_url == "https://x.y/z"
    assert parse_finding("prose " + json.dumps(payload) + " trailing").suggested_action == "REVIEW"


def test_parse_finding_normalises_and_rejects_garbage():
    finding = parse_finding('{"event_found": false, "event_type": "weird thing", "source_url": "not a url"}')
    assert finding.event_type == "OTHER" and finding.source_url is None and finding.suggested_action == "NO_CHANGE"
    with pytest.raises(AgentError):
        parse_finding("I could not find anything.")


# ---- OpenClaw adapter ----

REQUEST = AgentRequest(company_name="Acme Inspect", website="https://acme.example", concern="No proof pilots pay",
                       open_gap="Signed pilot agreements", last_review_date="2026-09-01",
                       investment_question="Are enterprise customers paying?")


def test_openclaw_requires_config():
    with pytest.raises(AgentError):
        OpenClawMonitoringAgent(gateway_url=None, token="t")
    with pytest.raises(AgentError):
        OpenClawMonitoringAgent(gateway_url="http://gw:18789", token=None)


def test_openclaw_builds_chat_completions_request():
    agent = OpenClawMonitoringAgent(gateway_url="http://gw:18789/", token="secret", agent_id="research")
    url, body, headers = agent.build_request(REQUEST)
    assert url == "http://gw:18789/v1/chat/completions"
    assert body["model"] == "openclaw/research" and body["stream"] is False
    assert headers["Authorization"] == "Bearer secret"
    user_text = body["messages"][1]["content"]
    assert "Acme Inspect" in user_text and "Are enterprise customers paying?" in user_text and "event_found" in user_text


async def test_openclaw_parses_gateway_reply():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        content = '```json\n{"event_found": true, "event_type": "FUNDING", "date": "2026-09-03", "summary": "Raised $4M seed.", "source_url": "https://news.example/acme", "relevance": "r", "claim_or_gap_affected": "funding", "suggested_action": "REVIEW"}\n```'
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": content}}]})

    agent = OpenClawMonitoringAgent(gateway_url="http://gw:18789", token="secret", transport=httpx.MockTransport(handler))
    finding = await agent.check_company(REQUEST)
    assert seen["auth"] == "Bearer secret" and seen["body"]["model"] == "openclaw/main"
    assert finding.event_type == "FUNDING" and finding.summary == "Raised $4M seed."


async def test_openclaw_surfaces_gateway_errors():
    agent = OpenClawMonitoringAgent(
        gateway_url="http://gw:18789", token="bad",
        transport=httpx.MockTransport(lambda r: httpx.Response(401, text="unauthorized")),
    )
    with pytest.raises(AgentError, match="401"):
        await agent.check_company(REQUEST)
