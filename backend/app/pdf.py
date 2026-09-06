"""PDF validation and page-level text extraction with PyMuPDF."""

from __future__ import annotations

from typing import TypedDict

import pymupdf

PDF_MAGIC = b"%PDF"


class PageText(TypedDict):
    page: int  # 1-based
    text: str


def validate_pdf_bytes(data: bytes, max_mb: int) -> None:
    if not data.startswith(PDF_MAGIC):
        raise ValueError("File is not a PDF (missing %PDF header).")
    if len(data) > max_mb * 1024 * 1024:
        raise ValueError(f"PDF exceeds the {max_mb} MB limit.")


def extract_pages(path: str, max_pages: int) -> list[PageText]:
    pages: list[PageText] = []
    with pymupdf.open(path) as doc:
        if doc.page_count > max_pages:
            raise ValueError(f"PDF has {doc.page_count} pages; limit is {max_pages}.")
        for page in doc:
            text = page.get_text("text", sort=True) or ""
            pages.append({"page": page.number + 1, "text": text.strip()})
    return pages


def pages_to_prompt_text(pages: list[PageText]) -> str:
    """Render pages with explicit markers so the model can cite page numbers."""
    chunks = [f"=== PAGE {p['page']} ===\n{p['text'] or '[no extractable text]'}" for p in pages]
    return "\n\n".join(chunks)
