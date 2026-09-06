import fitz
import pytest

from app.pdf import extract_pages, pages_to_prompt_text, validate_pdf_bytes


def make_pdf(path, texts):
    doc = fitz.open()
    for text in texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path


def test_extract_pages_returns_one_entry_per_page_with_1_based_numbers(tmp_path):
    pdf = make_pdf(tmp_path / "deck.pdf", ["Problem: manual review", "Traction: 2 pilots", "Ask: $1M"])
    pages = extract_pages(str(pdf), max_pages=200)
    assert [p["page"] for p in pages] == [1, 2, 3]
    assert "manual review" in pages[0]["text"]
    assert "2 pilots" in pages[1]["text"]


def test_extract_pages_rejects_too_many_pages(tmp_path):
    pdf = make_pdf(tmp_path / "big.pdf", ["a", "b", "c"])
    with pytest.raises(ValueError):
        extract_pages(str(pdf), max_pages=2)


def test_validate_rejects_non_pdf_and_oversize():
    with pytest.raises(ValueError):
        validate_pdf_bytes(b"hello", max_mb=1)
    with pytest.raises(ValueError):
        validate_pdf_bytes(b"%PDF" + b"0" * (2 * 1024 * 1024), max_mb=1)
    validate_pdf_bytes(b"%PDF-1.4 tiny", max_mb=1)


def test_prompt_text_has_page_markers():
    text = pages_to_prompt_text([{"page": 1, "text": "hello"}, {"page": 2, "text": ""}])
    assert "=== PAGE 1 ===" in text and "=== PAGE 2 ===" in text
    assert "[no extractable text]" in text
