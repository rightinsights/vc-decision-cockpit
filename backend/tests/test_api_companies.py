def test_create_list_get_company(client):
    created = client.post("/companies", json={"name": "  Acme  ", "website": "https://acme.example", "stage": "seed"})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Acme" and body["stage"] == "seed"
    assert body["created_at"].endswith("Z")

    listed = client.get("/companies").json()
    assert len(listed) == 1
    assert listed[0]["has_deck"] is False and listed[0]["decision"] is None

    assert client.get(f"/companies/{body['id']}").status_code == 200
    assert client.get("/companies/does-not-exist").status_code == 404


def test_create_company_requires_name(client):
    assert client.post("/companies", json={"name": ""}).status_code == 422


def test_upload_pdf_extracts_pages(client, deck_pdf):
    company = client.post("/companies", json={"name": "Acme"}).json()
    with open(deck_pdf, "rb") as fh:
        res = client.post(f"/companies/{company['id']}/deck", files={"file": ("acme deck (v2).pdf", fh, "application/pdf")})
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["page_count"] == 4
    assert doc["file_name"] == "acme_deck_v2_.pdf"
    assert client.get("/companies").json()[0]["has_deck"] is True


def test_upload_rejects_non_pdf(client):
    company = client.post("/companies", json={"name": "Acme"}).json()
    res = client.post(f"/companies/{company['id']}/deck", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert res.status_code == 400
    assert "not a PDF" in res.json()["detail"]


def test_thesis_seeded(client):
    thesis = client.get("/thesis").json()
    assert "deep domain expertise" in thesis["thesis_text"]
    assert len(thesis["criteria"]) == 9
    assert sum(c["weight"] for c in thesis["criteria"]) == 100
