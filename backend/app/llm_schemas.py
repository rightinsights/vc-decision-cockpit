"""
Pydantic models the LLM must return. Built for OpenAI strict structured outputs:
every field required (nullable via `| None`), no defaults, extra fields forbidden.
Range checks live in validators, not JSON-schema constraints, because strict mode
rejects minimum/maximum.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from .thesis import CRITERION_KEYS, CriterionKey

ClaimCategory = Literal[
    "traction", "market", "technology", "roi", "customer", "defensibility",
    "scalability", "team", "product", "business_model", "other",
]
Strength = Literal["LOW", "MEDIUM", "HIGH"]
Relation = Literal["SUPPORTS", "CONTRADICTS", "QUALIFIES"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- Deck extraction (BUILD_SPEC §6) ----

class ExtractedFounder(StrictModel):
    name: str
    role: str | None
    domain_background: str | None


class ExtractedClaim(StrictModel):
    claim: str
    category: ClaimCategory
    source_page: int | None
    supporting_text: str | None
    evidence_strength: Strength
    missing_proof: str | None


class DeckExtraction(StrictModel):
    company_name: str | None
    website: str | None
    stage: str | None
    geography: str | None
    founders: list[ExtractedFounder]
    problem: str | None
    workflow: str | None
    customer: str | None
    buyer: str | None
    solution: str | None
    business_model: str | None
    traction: list[str]
    funding_ask: str | None
    claims: list[ExtractedClaim]
    unknowns: list[str]


# ---- Thesis assessment (BUILD_SPEC §7) ----

class CriterionScore(StrictModel):
    key: CriterionKey
    score: int | None
    reason: str
    evidence_refs: list[str]

    @field_validator("score")
    @classmethod
    def _range(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 5:
            raise ValueError("score must be 1..5 or null")
        return value


class AssessmentOutput(StrictModel):
    criteria: list[CriterionScore]
    summary: str
    main_concern: str


def normalize_criteria(output: AssessmentOutput) -> dict[str, dict[str, Any]]:
    """Every criterion key present exactly once; missing ones become null (unknown)."""
    by_key = {c.key: c for c in output.criteria}
    result: dict[str, dict[str, Any]] = {}
    for key in CRITERION_KEYS:
        item = by_key.get(key)
        if item is None:
            result[key] = {"score": None, "reason": "Not assessed.", "evidence_refs": []}
        else:
            result[key] = {"score": item.score, "reason": item.reason, "evidence_refs": item.evidence_refs}
    return result


# ---- Diligence questions (BUILD_SPEC §8) ----

class DiligenceQuestionOut(StrictModel):
    question: str
    why_it_matters: str
    strong_answer: str
    weak_answer: str
    basis: str  # the claim, gap, contradiction, or criterion this question targets


class QuestionSet(StrictModel):
    questions: list[DiligenceQuestionOut]


# ---- Founder note analysis (BUILD_SPEC §9) ----

class NewEvidence(StrictModel):
    evidence_text: str
    relation: Relation
    claim_id: str | None
    criterion: CriterionKey | None


class NoteAnalysis(StrictModel):
    new_evidence: list[NewEvidence]
    contradictions: list[str]
    summary: str


# ---- Public research from Brave results ----

FactCategory = Literal[
    "COMPANY", "PRODUCT", "CUSTOMERS", "TRACTION", "FUNDING", "TEAM", "COMPETITORS", "RISKS", "OTHER",
]


class ResearchFactOut(StrictModel):
    category: FactCategory
    finding: str
    source_url: str  # must be one of the provided result URLs; enforced in code
    source_title: str
    publication_date: str | None
    confidence: Strength
    claim_id: str | None
    relation: Relation | None


class ResearchSnapshot(StrictModel):
    """Company profile fields derivable from the search results only. Null when the results do not say."""
    problem: str | None
    workflow: str | None
    customer: str | None
    buyer: str | None
    solution: str | None
    business_model: str | None
    founders: list[ExtractedFounder]
    traction: list[str]
    funding_ask: str | None
    stage: str | None
    geography: str | None


class ResearchReport(StrictModel):
    summary: str
    facts: list[ResearchFactOut]
    unknowns: list[str]
    entity_note: str | None  # e.g. "results about a different company named X were ignored"
    snapshot: ResearchSnapshot


# ---- Agent finding (BUILD_SPEC §10) ----

class AgentFinding(StrictModel):
    event_found: bool
    event_type: str
    date: str | None
    summary: str
    source_url: str | None
    relevance: str
    claim_or_gap_affected: str | None
    suggested_action: Literal["NO_CHANGE", "REVIEW"]
