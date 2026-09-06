from app.llm_schemas import AssessmentOutput, DeckExtraction, NewEvidence, NoteAnalysis
from tests.conftest import CANNED_SCORES, canned_assessment, canned_extraction, create_company_with_deck, install_fake_llm


def _scores(**overrides):
    scores = dict(CANNED_SCORES)
    scores.update(overrides)
    return scores


def test_timeline_orders_events_and_shows_before_after(client, deck_pdf):
    install_fake_llm({
        DeckExtraction: canned_extraction(),
        AssessmentOutput: [canned_assessment(), canned_assessment(_scores(customer_evidence=4, defensibility=5))],
    })
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    client.post(f"/companies/{cid}/analyze")
    client.post(f"/companies/{cid}/decisions", json={"decision": "WATCH", "rationale": "No customer proof yet"})
    client.post(f"/companies/{cid}/agent-check", json={})

    timeline = client.get(f"/companies/{cid}/changes").json()
    kinds = [e["kind"] for e in timeline]
    assert kinds == ["DECK_UPLOADED", "ASSESSMENT", "DECISION", "AGENT_EVENT", "ASSESSMENT"]
    assert [e["ts"] for e in timeline] == sorted(e["ts"] for e in timeline)

    initial = timeline[1]
    assert initial["title"] == "Initial deck analysis" and initial["recommendation"] == "WATCH"
    assert initial["deltas"] == [] and initial["human_decision_at_time"] is None

    reassessed = timeline[4]
    assert reassessed["title"] == "AI view updated after agent finding"
    assert reassessed["recommendation_before"] == "WATCH" and reassessed["recommendation"] == "DILIGENCE"
    assert reassessed["overall_score"] == 70  # 230 + 20 + 30 = 280 weighted quarter-points -> 70
    assert {d["key"]: (d["old"], d["new"]) for d in reassessed["deltas"]} == {"customer_evidence": (2, 4), "defensibility": (3, 5)}
    assert reassessed["human_decision_at_time"] == "WATCH"  # human decision untouched by the AI change
    assert timeline[3]["source_url"].startswith("https://")


def test_founder_note_reassessment_returns_diff(client, deck_pdf):
    fake = install_fake_llm({
        DeckExtraction: canned_extraction(),
        AssessmentOutput: [canned_assessment(), canned_assessment(_scores(customer_evidence=3), concern="Expansion unproven.")],
        NoteAnalysis: NoteAnalysis(
            new_evidence=[
                NewEvidence(evidence_text="Both pilots are paid: $30K and $50K.", relation="SUPPORTS", claim_id="unknown-id",
                            criterion="customer_evidence"),
                NewEvidence(evidence_text="Pilot customers plan to expand if first deployment works.", relation="QUALIFIES",
                            claim_id=None, criterion=None),
            ],
            contradictions=[],
            summary="Pilots confirmed as paid.",
        ),
    })
    company = create_company_with_deck(client, deck_pdf)
    cid = company["id"]
    client.post(f"/companies/{cid}/analyze")
    client.post(f"/companies/{cid}/decisions", json={"decision": "WATCH", "rationale": "Waiting on pilots"})

    note = client.post(f"/companies/{cid}/founder-notes", json={"raw_notes": "Founder says both pilots are paid. One is $30K and one is $50K."})
    assert note.status_code == 201, note.text
    res = client.post(f"/companies/{cid}/reassess", json={"note_id": note.json()["id"]})
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["trigger"] == "FOUNDER_NOTE" and body["event"] is None
    assert body["note_summary"] == "Pilots confirmed as paid."
    assert [e["source_type"] for e in body["new_evidence"]] == ["FOUNDER_NOTE", "FOUNDER_NOTE"]
    assert body["new_evidence"][0]["claim_id"] is not None  # bad id fell back to word-overlap match on 'pilots'
    assert body["deltas"] == [{"key": "customer_evidence", "label": "Customer evidence", "old": 2, "new": 3,
                               "reason": "reason for customer_evidence (p2)"}]
    assert body["assessment_after"]["overall_score"] == 60
    assert body["recommendation"]["changed"] is False
    assert body["human_decision"]["decision"] == "WATCH"
    assert "Founder update added 2 pieces of evidence" in body["explanation"]

    note_call = next(v for name, v in fake.calls if name == "note_analysis")
    assert "$30K" in note_call["notes"]
    reassess_call = [v for name, v in fake.calls if name == "assessment"][1]
    assert "FOUNDER NOTE" in reassess_call["extra_context"] and "SUPPORTS" in reassess_call["extra_context"]

    timeline = client.get(f"/companies/{cid}/changes").json()
    assert [e["kind"] for e in timeline] == ["DECK_UPLOADED", "ASSESSMENT", "DECISION", "FOUNDER_NOTE", "ASSESSMENT"]


def test_reassess_rejects_foreign_note(client, deck_pdf):
    install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment()})
    a = create_company_with_deck(client, deck_pdf, name="A")
    b = client.post("/companies", json={"name": "B"}).json()
    client.post(f"/companies/{a['id']}/analyze")
    note = client.post(f"/companies/{b['id']}/founder-notes", json={"raw_notes": "Some notes about company B here."}).json()
    assert client.post(f"/companies/{a['id']}/reassess", json={"note_id": note["id"]}).status_code == 404
