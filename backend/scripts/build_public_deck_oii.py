"""
Rebuild the Oii.ai seed deck (published by TechCrunch with the company's consent, June 2023) as a
text-searchable PDF: download each public slide image, transcribe it with the vision model, and
write one page per slide holding the image plus its transcription. Provenance is printed on every page.
"""
import base64
import sys
import time
from pathlib import Path

import httpx
import pymupdf
from openai import OpenAI

from app.config import get_settings

SRC = "https://techcrunch.com/2023/06/02/sample-seed-pitch-deck-oii-ai/"
BASE = "https://techcrunch.com/wp-content/uploads/2023/05/OII-AIPitchDeckTeardownTechCrunchslide-{}.jpg"
OUT_DIR = Path(__file__).parent / "decks" / "oii"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = Path(__file__).parent / "decks" / "oii-ai-seed-deck-2023-techcrunch.pdf"
HEADERS = {"User-Agent": "Mozilla/5.0 (research; one-off download of publicly posted slides)"}

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)
model = settings.openai_model

# 1. download
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
# TechCrunch published 7 of the 21 slides with the company's consent; the rest are view-only on Drive.

# 2. transcribe
PROMPT = (
    "Transcribe every piece of text on this pitch-deck slide verbatim, keeping the reading order and "
    "line structure. For charts, diagrams, logos, or tables, add a short bracketed description such as "
    "[chart: ...] with any numbers shown. Do not add commentary, do not summarise, do not invent text. "
    "If the slide has no text, reply [no text]."
)
transcripts: list[tuple[str, str]] = []
for name, path in slides:
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
    print(f"{name}: {len(text)} chars, {int((time.perf_counter()-t0)*1000)} ms, tokens={resp.usage.total_tokens if resp.usage else '?'}")

# 3. build PDF: image on top, transcription below, provenance footer
doc = pymupdf.open()
W, H = 612, 792
for idx, ((name, path), (_, text)) in enumerate(zip(slides, transcripts), start=1):
    page = doc.new_page(width=W, height=H)
    label = "cover" if name == "COVER" else f"original slide {int(name)}"
    page.insert_text((36, 30), f"Oii.ai seed deck (2023), {label}; {len(slides)} of 21 slides were published by TechCrunch with the company's consent. Source: {SRC}", fontsize=6.5, color=(0.4, 0.4, 0.4))
    img_rect = pymupdf.Rect(36, 40, W - 36, 40 + (W - 72) * 9 / 16)
    page.insert_image(img_rect, filename=str(path))
    text_rect = pymupdf.Rect(36, img_rect.y1 + 12, W - 36, H - 36)
    page.insert_textbox(text_rect, text or "[no text]", fontsize=8.5, fontname="helv", lineheight=1.25)
doc.save(str(PDF_PATH))
doc.close()

check = pymupdf.open(str(PDF_PATH))
print("pdf:", PDF_PATH, "pages", check.page_count, "chars", sum(len(p.get_text()) for p in check))
