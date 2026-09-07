"""
Vision fallback for image-only deck pages. Pages with almost no extractable text are rendered
and transcribed by the vision model, so an exported-as-images deck still yields claims with slide
references instead of a company named after the only logo with live text.
"""

from __future__ import annotations

from typing import Protocol

import pymupdf

from .pdf import PageText

MIN_CHARS_FOR_TEXT = 40      # below this a page is treated as image-only
MAX_TILE_PX = 1800           # longest side per rendered tile
TRANSCRIBE_PROMPT = (
    "Transcribe every piece of text on this pitch-deck slide verbatim, keeping the reading order and line structure. "
    "For charts, diagrams, logos, or tables, add a short bracketed description such as [chart: ...] with any numbers shown. "
    "Do not add commentary, do not summarise, do not invent text. If the slide has no text, reply [no text]."
)


class Transcriber(Protocol):
    def transcribe_image(self, png_bytes: bytes, prompt: str) -> str: ...


def render_tiles(page: pymupdf.Page, max_side: int = MAX_TILE_PX) -> list[bytes]:
    """Render a page to one or more PNG tiles no larger than max_side on the long edge (tall one-pagers get split)."""
    rect = page.rect
    if rect.height <= rect.width * 1.6:  # normal slide: one tile
        scale = min(max_side / max(rect.width, rect.height), 3.0)
        return [page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")]
    # tall page: tile vertically at a scale that keeps width readable
    scale = max_side / rect.width
    scale = min(scale, 3.0)
    tile_h = max_side / scale
    tiles: list[bytes] = []
    y = rect.y0
    while y < rect.y1:
        clip = pymupdf.Rect(rect.x0, y, rect.x1, min(y + tile_h, rect.y1))
        tiles.append(page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False).tobytes("png"))
        y += tile_h
    return tiles


def transcribe_image_pages(path: str, pages: list[PageText], transcriber: Transcriber, *, min_chars: int = MIN_CHARS_FOR_TEXT) -> tuple[list[PageText], int]:
    """Replace the text of image-only pages with vision transcriptions. Returns (pages, count_transcribed)."""
    needs = [p["page"] for p in pages if len((p.get("text") or "").strip()) < min_chars]
    if not needs:
        return pages, 0
    updated = [dict(p) for p in pages]
    with pymupdf.open(path) as doc:
        for page_no in needs:
            page = doc[page_no - 1]
            chunks = [transcriber.transcribe_image(tile, TRANSCRIBE_PROMPT).strip() for tile in render_tiles(page)]
            text = "\n".join(c for c in chunks if c and c != "[no text]")
            original = (updated[page_no - 1].get("text") or "").strip()
            updated[page_no - 1]["text"] = (text or original).strip()
            updated[page_no - 1]["ocr"] = True
    return updated, len(needs)  # type: ignore[return-value]
