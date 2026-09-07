"""The investment thesis: text, criteria, weights, and recommendation bands (BUILD_SPEC §2, §7)."""

from __future__ import annotations

import hashlib
import json
from typing import Literal, TypedDict

THESIS_NAME = "Domain-expert AI for overlooked technical workflows (v2)"

THESIS_TEXT = (
    "I want to invest in pre-seed and seed companies across North America, and selectively "
    "Europe, where founders with deep domain expertise use AI, software, and proprietary data "
    "to automate complex, overlooked workflows in technical, industrial, and regulated sectors."
)

# "What I am looking for"
POSITIVE_SIGNALS = [
    "Stage: pre-seed and seed. Selective Series A only when product-market fit or commercialization is still being established.",
    "Geography: North America, with selective opportunities in Europe. Chicago and the Midwest are the strongest ecosystem base.",
    "Founder: deep firsthand knowledge of the workflow and the customer environment.",
    "Problem: expensive, repetitive, fragmented, manual, or expert-heavy work that still depends on spreadsheets, email, "
    "legacy systems, consultants, or institutional memory.",
    "Product: AI, software, proprietary data, or a combination that clearly improves speed, cost, accuracy, risk, capacity, "
    "or decision quality.",
    "Defensibility: proprietary data, deep workflow integration, accumulated customer intelligence, domain-specific models, "
    "or becoming a system of record or system of action.",
]

# "What is outside my focus"
OUT_OF_SCOPE = [
    "Generic horizontal SaaS",
    "General-purpose chatbots",
    "Consumer marketplaces, social media, dating apps, consumer brands",
    "Health foods",
    "Biotechnology, genetics, pharmaceuticals, and chemistry-led life sciences",
]

INVESTOR_NOTE = (
    "A career spent evaluating technologies and moving ideas toward products: engineering, research, patents, IP strategy, "
    "technical intelligence, commercialization, corporate innovation, universities, and startups, plus a founder's view "
    "from building Strata IP. The aim over the next two years: a clear, repeatable thesis; a real pipeline of thesis-aligned "
    "founders; a shadow track record of written invest and pass decisions; measurable help to founders; a stronger LP and "
    "investor network; and a credible path to active investing and a fund. AI speeds up research and routine work here. "
    "It is not a substitute for judgment."
)

CriterionKey = Literal[
    "founder_domain_fit",
    "workflow_pain",
    "workflow_frequency",
    "buyer_clarity",
    "customer_evidence",
    "roi_clarity",
    "defensibility",
    "scalability",
    "stage_geography_fit",
]

Recommendation = Literal["PASS", "WATCH", "DILIGENCE"]


class Criterion(TypedDict):
    key: str
    label: str
    weight: int
    description: str


CRITERIA: list[Criterion] = [
    {"key": "founder_domain_fit", "label": "Founder-domain fit", "weight": 15,
     "description": "Founders have firsthand, expert knowledge of the workflow and its customer environment."},
    {"key": "workflow_pain", "label": "Workflow pain", "weight": 15,
     "description": "The work is expensive, repetitive, fragmented, manual, or expert-heavy, and still runs on spreadsheets, "
                    "email, legacy systems, consultants, or institutional memory."},
    {"key": "workflow_frequency", "label": "Workflow frequency", "weight": 10,
     "description": "The workflow happens often enough to matter and to generate usage data."},
    {"key": "buyer_clarity", "label": "Buyer clarity", "weight": 10,
     "description": "A specific customer and a specific buyer with budget are identified."},
    {"key": "customer_evidence", "label": "Customer evidence", "weight": 10,
     "description": "Real customers, pilots, revenue, or usage, not just interest."},
    {"key": "roi_clarity", "label": "ROI clarity", "weight": 10,
     "description": "Measurable value in speed, cost, accuracy, risk, capacity, or decision quality."},
    {"key": "defensibility", "label": "Defensibility", "weight": 15,
     "description": "Proprietary data, deep workflow integration, accumulated customer intelligence, domain-specific models, "
                    "or a system-of-record or system-of-action position."},
    {"key": "scalability", "label": "Scalability", "weight": 10,
     "description": "Software-like margins and repeatable deployment, not services-heavy delivery."},
    {"key": "stage_geography_fit", "label": "Stage/geography fit", "weight": 5,
     "description": "Pre-seed or seed (selective Series A); North America, Midwest strongest, selective Europe."},
]

WEIGHTS: dict[str, int] = {c["key"]: c["weight"] for c in CRITERIA}
LABELS: dict[str, str] = {c["key"]: c["label"] for c in CRITERIA}
CRITERION_KEYS: list[str] = [c["key"] for c in CRITERIA]

assert sum(WEIGHTS.values()) == 100, "criterion weights must sum to 100"

# Recommendation bands (inclusive lower bounds), BUILD_SPEC §7.
BANDS: list[tuple[int, Recommendation]] = [(70, "DILIGENCE"), (50, "WATCH"), (0, "PASS")]


def band(overall: int) -> Recommendation:
    for floor, label in BANDS:
        if overall >= floor:
            return label
    return "PASS"


def criteria_payload() -> dict:
    return {
        "criteria": CRITERIA,
        "positive_signals": POSITIVE_SIGNALS,
        "out_of_scope": OUT_OF_SCOPE,
        "investor_note": INVESTOR_NOTE,
        "bands": [{"min": floor, "recommendation": label} for floor, label in BANDS],
    }


def thesis_fingerprint() -> str:
    """Changes whenever the thesis text or criteria change; used to append a new thesis version row."""
    blob = json.dumps({"name": THESIS_NAME, "text": THESIS_TEXT, "payload": criteria_payload()}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
