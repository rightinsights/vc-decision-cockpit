import io

import pymupdf
from sqlalchemy import create_engine, inspect, text

from app.db import Base
from app.llm_schemas import AssessmentOutput, DeckExtraction
from app.migrate import ensure_columns
from app.ocr import render_tiles, transcribe_image_pages
from app.seed import seed_thesis
from app import thesis as T
from tests.conftest import canned_assessment, canned_extraction, install_fake_llm


def image_only_pdf(tmp_path, tall=False):
    doc = pymupdf.open()
    width, height = (600, 3400) if tall else (612, 792)
    page = doc.new_page(width=width, height=height)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 120), False)
    pix.clear_with(200)
    page.insert_image(pymupdf.Rect(50, 50, 550, 350), pixmap=pix)
    path = tmp_path / ("tall.pdf" if tall else "image.pdf")
    doc.save(str(path))
    doc.close()
    return path


def test_render_tiles_splits_tall_pages(tmp_path):
    with pymupdf.open(str(image_only_pdf(tmp_path, tall=True))) as doc:
        tiles = render_tiles(doc[0], max_side=800)
        assert len(tiles) >= 3
        assert all(t.startswith(b"\x89PNG") for t in tiles)
    with pymupdf.open(str(image_only_pdf(tmp_path))) as doc:
        assert len(render_tiles(doc[0], max_side=800)) == 1


def test_transcribe_only_pages_without_text(tmp_path):
    class Fake:
        calls = 0

        def transcribe_image(self, png, prompt):
            Fake.calls += 1
            return "Transcribed slide text"

    path = image_only_pdf(tmp_path)
    pages = [{"page": 1, "text": ""}]
    out, count = transcribe_image_pages(str(path), pages, Fake())
    assert count == 1 and out[0]["text"] == "Transcribed slide text" and out[0]["ocr"] is True
    out, count = transcribe_image_pages(str(path), [{"page": 1, "text": "x" * 80}], Fake())
    assert count == 0 and "ocr" not in out[0]


def test_upload_transcribes_image_only_deck_end_to_end(client, tmp_path):
    fake = install_fake_llm({DeckExtraction: canned_extraction(), AssessmentOutput: canned_assessment()},
                            transcription="Acme Inspect. Two paid pilots with regional utilities.")
    company = client.post("/companies", json={"name": "Acme"}).json()
    with open(image_only_pdf(tmp_path), "rb") as fh:
        res = client.post(f"/companies/{company['id']}/deck", files={"file": ("scan.pdf", fh, "application/pdf")})
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["page_count"] == 1 and doc["ocr_pages"] == 1
    assert len(fake.transcribed) == 1
    res = client.post(f"/companies/{company['id']}/analyze")
    assert res.status_code == 200
    extraction_call = next(v for name, v in fake.calls if name == "extraction")
    assert "Two paid pilots" in extraction_call["deck_text"]


def test_ensure_columns_adds_missing_column(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documents (id TEXT PRIMARY KEY, file_name TEXT)"))
    applied = ensure_columns(engine)
    assert applied == ["documents.ocr_pages"]
    assert "ocr_pages" in {c["name"] for c in inspect(engine).get_columns("documents")}
    assert ensure_columns(engine) == []  # idempotent


def test_thesis_reseeds_as_new_version_when_content_changes(client):
    from app.db import SessionLocal
    with SessionLocal() as db:
        first = seed_thesis(db)
        again = seed_thesis(db)
        assert again.id == first.id
        # simulate an older stored version: strip the fingerprint, as a pre-v2 row would have
        first.criteria_json = {k: v for k, v in first.criteria_json.items() if k != "fingerprint"}
        db.commit()
        newer = seed_thesis(db)
        assert newer.id != first.id and newer.name == T.THESIS_NAME
    thesis = client.get("/thesis").json()
    assert "Chicago" in " ".join(thesis["positive_signals"])
    assert thesis["investor_note"].startswith("A career")
