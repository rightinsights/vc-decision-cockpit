"""API request/response models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

DecisionValue = Literal["PASS", "WATCH", "DILIGENCE"]


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Thesis ----

class ThesisOut(OrmModel):
    id: str
    name: str
    thesis_text: str
    criteria: list[dict[str, Any]]
    positive_signals: list[str]
    out_of_scope: list[str]


# ---- Companies ----

class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = None
    stage: str | None = None
    geography: str | None = None

    @field_validator("name", "website", "stage", "geography", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None if value == "" else value
        return value


class CompanyOut(OrmModel):
    id: str
    name: str
    website: str | None
    stage: str | None
    geography: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class PipelineRow(CompanyOut):
    has_deck: bool
    has_analysis: bool
    recommendation: str | None
    overall_score: int | None
    decision: str | None
    main_concern: str | None
    last_changed: UtcDateTime


class DocumentOut(OrmModel):
    id: str
    company_id: str
    file_name: str
    page_count: int
    created_at: UtcDateTime


# ---- Claims / evidence ----

class EvidenceOut(OrmModel):
    id: str
    claim_id: str | None
    evidence_text: str
    relation: str
    source_page: int | None
    source_url: str | None
    source_type: str
    created_at: UtcDateTime


class ClaimOut(OrmModel):
    id: str
    claim_text: str
    category: str
    source_page: int | None
    supporting_text: str | None
    evidence_strength: str
    missing_proof: str | None
    evidence: list[EvidenceOut]


# ---- Assessment / questions / decisions ----

class AssessmentOut(OrmModel):
    id: str
    trigger: str
    source_ref_id: str | None
    criterion_scores: dict[str, Any] = Field(validation_alias="criterion_scores_json")
    overall_score: int | None
    used_weight: int
    recommendation: str | None
    summary: str
    main_concern: str
    created_at: UtcDateTime


class QuestionOut(OrmModel):
    id: str
    position: int
    question: str
    why_it_matters: str
    strong_answer: str
    weak_answer: str
    basis: str


class DecisionCreate(BaseModel):
    decision: DecisionValue
    rationale: str

    @field_validator("rationale")
    @classmethod
    def _require_rationale(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("A short rationale is required.")
        return value


class DecisionOut(OrmModel):
    id: str
    decision: str
    rationale: str
    assessment_id: str | None
    created_at: UtcDateTime


class MonitoringEventOut(OrmModel):
    id: str
    agent_provider: str
    investment_question: str
    event_found: bool
    event_type: str
    event_date: str | None
    summary: str
    source_url: str | None
    relevance: str
    claim_or_gap_affected: str | None
    suggested_action: str
    created_at: UtcDateTime


class AnalysisOut(BaseModel):
    company: CompanyOut
    snapshot: dict[str, Any] | None
    document: DocumentOut | None
    claims: list[ClaimOut]
    assessment: AssessmentOut | None
    questions: list[QuestionOut]
    decision: DecisionOut | None
    thesis: ThesisOut
    monitoring_events: list[MonitoringEventOut]
    research: "ResearchOut | None" = None


# ---- Agent check / reassessment ----

class AgentCheckRequest(BaseModel):
    investment_question: str | None = None


class RecommendationChange(BaseModel):
    before: str | None
    after: str | None
    changed: bool


class ReassessmentOut(BaseModel):
    """Before -> new evidence -> after. Shared by agent check, founder-note, and research reassessment."""
    trigger: Literal["AGENT", "FOUNDER_NOTE", "RESEARCH"]
    event: MonitoringEventOut | None
    note_summary: str | None
    new_evidence: list[EvidenceOut]
    assessment_before: AssessmentOut | None
    assessment_after: AssessmentOut
    deltas: list[dict[str, Any]]
    recommendation: RecommendationChange
    human_decision: DecisionOut | None
    matters: bool
    explanation: str


class FounderNoteCreate(BaseModel):
    raw_notes: str = Field(min_length=10)


class FounderNoteOut(OrmModel):
    id: str
    raw_notes: str
    created_at: UtcDateTime


class ResearchRequest(BaseModel):
    brief: str | None = None


class ResearchFactView(BaseModel):
    category: str
    finding: str
    source_url: str
    source_title: str
    publication_date: str | None = None
    confidence: str
    claim_id: str | None = None
    relation: str | None = None


class ResearchOut(BaseModel):
    id: str
    brief: str
    queries: list[str]
    result_count: int
    domain_count: int
    facts_kept: int
    facts_dropped: int
    search_provider: str
    summary: str
    entity_note: str | None
    facts: list[ResearchFactView]
    unknowns: list[str]
    created_at: UtcDateTime
    reassessment: ReassessmentOut | None = None


class ChangeEntry(BaseModel):
    id: str
    ts: UtcDateTime
    kind: Literal[
        "DECK_UPLOADED", "ASSESSMENT", "DECISION", "AGENT_EVENT", "FOUNDER_NOTE", "QUESTIONS", "RESEARCH",
    ]
    title: str
    detail: str
    source_url: str | None = None
    recommendation: str | None = None
    overall_score: int | None = None
    deltas: list[dict[str, Any]] = Field(default_factory=list)
    recommendation_before: str | None = None
    human_decision_at_time: str | None = None
