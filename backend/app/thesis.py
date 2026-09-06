"""The investment thesis: text, criteria, weights, and recommendation bands (BUILD_SPEC §2, §7)."""

from __future__ import annotations

from typing import Literal, TypedDict

THESIS_NAME = "Domain-expert AI for overlooked technical workflows (v1)"

THESIS_TEXT = (
    "I want to invest in pre-seed and seed companies across North America, and selectively "
    "Europe, where founders with deep domain expertise use AI, software, and proprietary data "
    "to automate complex, overlooked workflows in technical, industrial, and regulated sectors."
)

POSITIVE_SIGNALS = [
    "Pre-seed or seed",
    "North America or selective Europe",
    "Founder has real domain/workflow knowledge",
    "Painful, frequent, manual, fragmented, or expert-heavy workflow",
    "Clear customer and buyer",
    "Measurable value in time, cost, accuracy, risk, capacity, or decision quality",
    "Defensibility through proprietary data, workflow integration, IP, customer intelligence, "
    "switching costs, or system-of-record/action position",
]

OUT_OF_SCOPE = [
    "Generic horizontal SaaS",
    "General-purpose chatbots",
    "Consumer social or dating",
    "Consumer brands and marketplaces",
    "Biotechnology, genetics, pharmaceuticals, or chemistry-led life sciences",
]

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
     "description": "Founders have firsthand, expert knowledge of the workflow and its customer."},
    {"key": "workflow_pain", "label": "Workflow pain", "weight": 15,
     "description": "The workflow is painful, expensive, manual, fragmented, or expert-heavy."},
    {"key": "workflow_frequency", "label": "Workflow frequency", "weight": 10,
     "description": "The workflow happens often enough to matter and to generate usage data."},
    {"key": "buyer_clarity", "label": "Buyer clarity", "weight": 10,
     "description": "A specific customer and a specific buyer with budget are identified."},
    {"key": "customer_evidence", "label": "Customer evidence", "weight": 10,
     "description": "Real customers, pilots, revenue, or usage, not just interest."},
    {"key": "roi_clarity", "label": "ROI clarity", "weight": 10,
     "description": "Measurable value in time, cost, accuracy, risk, capacity, or decision quality."},
    {"key": "defensibility", "label": "Defensibility", "weight": 15,
     "description": "Proprietary data, workflow integration, IP, switching costs, or system-of-record position."},
    {"key": "scalability", "label": "Scalability", "weight": 10,
     "description": "Software-like margins and repeatable deployment, not services-heavy delivery."},
    {"key": "stage_geography_fit", "label": "Stage/geography fit", "weight": 5,
     "description": "Pre-seed or seed; North America or selective Europe."},
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
