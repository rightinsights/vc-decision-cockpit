import json

import httpx
import pytest

from app.llm_schemas import AssessmentOutput, DeckExtraction, ResearchFactOut, ResearchReport, ResearchSnapshot
from app.services.brave import BraveClient, ResearchError, build_queries, gather_results, get_brave
from app.main import app
from tests.conftest import CANNED_SCORES, canned_assessment, canned_extraction, create_company_with_deck, error_of, install_fake_llm

RESULTS = {
    "web": {"results": [
        {"title": "Acme Inspect | Home", "url": "https://acmeinspect.example/", "description": "AI weld inspection reports.", "age": None},
        {"title": "Acme Inspect signs two utility pilots", "url": "https://news.example/acme-pilots",
         "description": "Two regional gas utilities have started paid pilots.", "page_age": "2026-08-20"},
        {"title": "Acme Inspect | Home", "url": "https://acmeinspect.example", "description": "duplicate", "age": None},
    ]}
}


def brave_transport(status=200, body=None):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        assert request.headers["X-Subscription-Token"] == "brave-key"
        return httpx.Response(status, json=body if body is not None else RESULTS)

    return httpx.MockTransport(handler), calls


def install_brave(client_obj):
    app.dependency_overrides[get_brave] = lambda: client_obj


@pytest.fixture(autouse=True)
def _clear_brave_override():
    yield
    app.dependency_overrides.pop(get_brave, None)


def canned_report(extra_url="https://news.example/acme-pilots", claim_id=None):
    return ResearchReport(
        summary="Acme Inspect is a seed-stage weld inspection software company with two reported utility pilots.",
        facts=[
            ResearchFactOut(category="TRACTION", finding="Two regional gas utilities have started paid pilots.",
                            source_url=extra_url, source_title="Acme Inspect signs two utility pilots",
                            publication_date="2026-08-20", confidence="MEDIUM", claim_id=claim_id, relation="SUPPORTS" if claim_id else None),
            ResearchFactOut(category="FUNDING", finding="Raised a $9M Series A led by a top fund.",
                            source_url="https://made-up.example/funding", source_title="Fabricated",
                            publication_date=None, confidence="HIGH", claim_id=None, relation=None),
        ],
        unknowns=["Founder backgrounds"],
        entity_note=None,
        snapshot=ResearchSnapshot(problem="Weld reports are re-keyed by hand.", workflow="Post-inspection reporting", customer="Pipeline operators",
                                  buyer=None, solution="AI-drafted inspection reports", business_model=None, founders=[], traction=["Two utility pilots"],
                                  funding_ask=None, stage="seed", geography="United States"),
    )


# ---- Brave client ----

def test_build_queries_uses_domain_and_brief_keywords():
    queries = build_queries("Acme Inspect", "https://www.acmeinspect.example/about", "founders, customers, and material risks")
    assert queries[0] == '"Acme Inspect" acmeinspect.example'
    assert "funding OR customers" in queries[1]
    assert queries[2] == '"Acme Inspect" founders customers material risks'


async def test_gather_results_dedupes_by_url_and_sends_key():
    transport, calls = brave_transport()
    client = BraveClient("brave-key", count=8, transport=transport)
    results = await gather_results(client, ["q1", "q2"])
    assert len(calls) == 2 and calls[0]["q"] == "q1"
    assert [r["url"] for r in results] == ["https://acmeinspect.example/", "https://news.example/acme-pilots"]
    assert results[1]["age"] == "2026-08-20"


async def test_brave_errors_are_explicit():
    with pytest.raises(ResearchError, match="BRAVE_API_KEY"):
        BraveClient(None)
    transport, _ = brave_transport(status=401, body={"message": "nope"})
    with pytest.raises(ResearchError, match="401"):
        await BraveClient("brave-key", transport=transport).search("x")
    transport, _ = brave_transport(status=429, body={})
    with pytest.raises(ResearchError, match="429"):
        await BraveClient("brave-key", transport=transport).search("x")


# ---- research endpoint ----

def test_research_without_deck_keeps_only_sourced_facts(client):
    fake = install_fake_llm({ResearchReport: canned_report(), AssessmentOutput: canned_assessment()})
    transport, _ = brave_transport()
    install_brave(BraveClient("brave-key", transport=transport))
    company = client.post("/companies", json={"name": "Acme Inspect", "website": "https://acmeinspect.example"}).json()

    res = client.post(f"/companies/{company['id']}/research", json={"brief": "customers and funding"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["search_provider"] == "brave"
    assert body["result_count"] == 2 and body["domain_count"] == 2
    assert body["facts_kept"] == 1 and body["facts_dropped"] == 1  # fabricated URL dropped
    assert body["facts"][0]["source_url"] == "https://news.example/acme-pilots"
    assert body["snapshot_applied"] is True and body["initial_assessment"] is True
    assert body["reassessment"]["assessment_before"] is None  # first thesis fit came from public sources
    assert body["reassessment"]["assessment_after"]["trigger"] == "RESEARCH"
    assert body["unknowns"] == ["Founder backgrounds"]

    prompt_vars = next(v for name, v in fake.calls if name == "research")
    sent = json.loads(prompt_vars["results_json"])
    assert [r["url"] for r in sent] == ["https://acmeinspect.example/", "https://news.example/acme-pilots"]
    assert "customers and funding" in prompt_vars["brief"]

    fetched = client.get(f"/companies/{company['id']}/research").json()
    assert fetched["id"] == body["id"]
    analysis = client.get(f"/companies/{company['id']}/analysis").json()
    assert analysis["research"]["facts_kept"] == 1
    assert analysis["snapshot"]["problem"] == "Weld reports are re-keyed by hand." and analysis["snapshot"]["source"] == "web"
    assert analysis["company"]["stage"] == "seed"
    assert analysis["assessment"]["trigger"] == "RESEARCH"
    assert [e["kind"] for e in client.get(f"/companies/{company['id']}/changes").json()] == ["RESEARCH", "ASSESSMENT"]


def test_research_after_deck_links_evidence_and_rescores(client, deck_pdf):
    after_scores = dict(CANNED_SCORES)
    after_scores["customer_evidence"] = 3
    install_fake_llm({
        DeckExtraction: canned_extraction(),
        AssessmentOutput: [canned_assessment(), canned_assessment(after_scores)],
        ResearchReport: canned_report(),
    })
    transport, _ = brave_transport()
    install_brave(BraveClient("brave-key", transport=transport))
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    client.post(f"/companies/{cid}/analyze")

    res = client.post(f"/companies/{cid}/research", json={})
    assert res.status_code == 200, res.text
    body = res.json()
    re = body["reassessment"]
    assert re["trigger"] == "RESEARCH"
    assert re["deltas"] == [{"key": "customer_evidence", "label": "Customer evidence", "old": 2, "new": 3,
                             "reason": "reason for customer_evidence (p2)"}]
    assert re["new_evidence"][0]["source_type"] == "WEB"
    assert "Public research added 1 sourced fact" in re["explanation"]

    # the WEB evidence landed on the pilots claim by word overlap and shows in the ledger
    analysis = client.get(f"/companies/{cid}/analysis").json()
    pilots = next(c for c in analysis["claims"] if c["category"] == "traction")
    web = [e for e in pilots["evidence"] if e["source_type"] == "WEB"]
    assert len(web) == 1 and web[0]["source_url"] == "https://news.example/acme-pilots"
    assert analysis["assessment"]["trigger"] == "RESEARCH"
    kinds = [e["kind"] for e in client.get(f"/companies/{cid}/changes").json()]
    assert kinds == ["DECK_UPLOADED", "ASSESSMENT", "RESEARCH", "ASSESSMENT"]


def test_research_reports_search_and_key_failures(client):
    install_fake_llm({ResearchReport: canned_report(), AssessmentOutput: canned_assessment()})
    company = client.post("/companies", json={"name": "Acme"}).json()
    assert client.get(f"/companies/{company['id']}/research").status_code == 404

    transport, _ = brave_transport(status=401, body={})
    install_brave(BraveClient("brave-key", transport=transport))
    res = client.post(f"/companies/{company['id']}/research", json={})
    status, detail = error_of(res)
    assert status == 502 and "401" in detail

    app.dependency_overrides.pop(get_brave, None)  # real dependency, no key configured in tests
    res = client.post(f"/companies/{company['id']}/research", json={})
    assert res.status_code == 400 and "BRAVE_API_KEY" in res.json()["detail"]
