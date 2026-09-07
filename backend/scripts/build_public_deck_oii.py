"""
Rebuild the Oii.ai seed deck as a text-searchable PDF from the 7 of 21 slides that TechCrunch
published with the company's consent (June 2023). Each public slide image is downloaded,
transcribed with the vision model (cached), and written as one page holding the image plus its
transcription. Provenance lives in PDF metadata and on a final notes page, never in slide text,
so the extractor does not read it as a founder claim.

    cd backend && .venv/bin/python -m scripts.build_public_deck_oii
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import httpx
import pymupdf
from openai import OpenAI

from app.config import get_settings

SRC = "https://techcrunch.com/2023/06/02/sample-seed-pitch-deck-oii-ai/"
BASE = "https://techcrunch.com/wp-content/uploads/2023/05/OII-AIPitchDeckTeardownTechCrunchslide-{}.jpg"
DATA = Path(__file__).resolve().parents[1] / "data" / "demo"
OUT_DIR = DATA / "oii-slides"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = DATA / "oii-ai-seed-deck-2023-techcrunch.pdf"
CACHE = OUT_DIR / "transcripts.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (research; one-off download of publicly posted slides)"}

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)
model = settings.openai_model

# 1. download the slides TechCrunch hosts (only some of the 21 exist at this pattern)
names = ["COVER"] + [f"{i:04d}" for i in range(1, 31)]
slides: list[tuple[str, Path]] = []
with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as http:
    for name in names:
        target = OUT_DIR / f"{name}.jpg"
        if not target.exists():
            r = http.get(BASE.format(name))
            if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
                continue
            target.write_bytes(r.content)
        slides.append((name, target))
print("slides found:", [n for n, _ in slides])
if len(slides) < 5:
    sys.exit("too few slides; check the URL pattern")

# 2. transcribe (cached so rebuilding the PDF costs nothing)
cached: dict[str, str] = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
PROMPT = (
    "Transcribe every piece of text on this pitch-deck slide verbatim, keeping the reading order and "
    "line structure. For charts, diagrams, logos, or tables, add a short bracketed description such as "
    "[chart: ...] with any numbers shown. Do not add commentary, do not summarise, do not invent text. "
    "If the slide has no text, reply [no text]."
)
transcripts: list[tuple[str, str]] = []
for name, path in slides:
    if name in cached:
        transcripts.append((name, cached[name]))
        print(f"{name}: cached, {len(cached[name])} chars")
        continue
    data = base64.b64encode(path.read_bytes()).decode()
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}", "detail": "high"}},
        ]}],
    )
    text = (resp.choices[0].message.content or "").strip()
    transcripts.append((name, text))
    cached[name] = text
    CACHE.write_text(json.dumps(cached, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{name}: {len(text)} chars, {int((time.perf_counter()-t0)*1000)} ms, tokens={resp.usage.total_tokens if resp.usage else '?'}")

# 3. build the PDF: image on top, transcription below; provenance in metadata and a final notes page
doc = pymupdf.open()
W, H = 612, 792
for (name, path), (_, text) in zip(slides, transcripts):
    page = doc.new_page(width=W, height=H)
    img_rect = pymupdf.Rect(36, 40, W - 36, 40 + (W - 72) * 9 / 16)
    page.insert_image(img_rect, filename=str(path))
    text_rect = pymupdf.Rect(36, img_rect.y1 + 12, W - 36, H - 36)
    page.insert_textbox(text_rect, text or "[no text]", fontsize=8.5, fontname="helv", lineheight=1.25)
notes = doc.new_page(width=W, height=H)
notes.insert_textbox(
    pymupdf.Rect(36, 36, W - 36, H - 36),
    "Provenance note (not part of the company's deck): the preceding pages reproduce the "
    f"{len(slides)} of 21 slides of Oii.ai's 2023 seed deck that TechCrunch published with the company's "
    f"consent at {SRC}. Slide text was transcribed from the published images. The remaining slides are "
    "not public and are not included.",
    fontsize=9, fontname="helv", lineheight=1.3,
)
doc.set_metadata({"title": "Oii.ai seed deck (2023), public slides via TechCrunch", "subject": SRC, "producer": "build_public_deck_oii.py"})
doc.save(str(PDF_PATH))
doc.close()

check = pymupdf.open(str(PDF_PATH))
print("pdf:", PDF_PATH, "pages", check.page_count, "chars", sum(len(p.get_text()) for p in check))
