"""SQLAlchemy models (BUILD_SPEC §11, plus the few columns the screens need)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    # Stored naive-UTC so SQLite and Postgres behave the same; serialized with a Z suffix.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Thesis(Base):
    __tablename__ = "thesis"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    thesis_text: Mapped[str] = mapped_column(Text)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geography: Mapped[str | None] = mapped_column(String(200), nullable=True)
    snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    documents: Mapped[list[Document]] = relationship(back_populates="company", cascade="all, delete-orphan")
    claims: Mapped[list[Claim]] = relationship(back_populates="company", cascade="all, delete-orphan")
    evidence: Mapped[list[Evidence]] = relationship(back_populates="company", cascade="all, delete-orphan")
    assessments: Mapped[list[Assessment]] = relationship(back_populates="company", cascade="all, delete-orphan")
    questions: Mapped[list[DiligenceQuestion]] = relationship(back_populates="company", cascade="all, delete-orphan")
    decisions: Mapped[list[Decision]] = relationship(back_populates="company", cascade="all, delete-orphan")
    founder_notes: Mapped[list[FounderNote]] = relationship(back_populates="company", cascade="all, delete-orphan")
    monitoring_events: Mapped[list[MonitoringEvent]] = relationship(back_populates="company", cascade="all, delete-orphan")
    research_runs: Mapped[list[ResearchRun]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(300))
    file_path: Mapped[str] = mapped_column(String(1000))
    page_count: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text)
    pages_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="documents")


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    claim_text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supporting_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_strength: Mapped[str] = mapped_column(String(10))
    missing_proof: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="claims")
    evidence: Mapped[list[Evidence]] = relationship(back_populates="claim", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), nullable=True, index=True)
    evidence_text: Mapped[str] = mapped_column(Text)
    relation: Mapped[str] = mapped_column(String(20))  # SUPPORTS / CONTRADICTS / QUALIFIES
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(String(20))  # DECK / FOUNDER_NOTE / AGENT
    source_ref_id: Mapped[str | None] = mapped_column(String(32), nullable=True)  # document / note / event id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="evidence")
    claim: Mapped[Claim | None] = relationship(back_populates="evidence")


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    thesis_id: Mapped[str | None] = mapped_column(ForeignKey("thesis.id"), nullable=True)
    trigger: Mapped[str] = mapped_column(String(20))  # DECK / AGENT / FOUNDER_NOTE
    source_ref_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    criterion_scores_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_weight: Mapped[int] = mapped_column(Integer, default=0)
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    main_concern: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="assessments")


class DiligenceQuestion(Base):
    __tablename__ = "diligence_questions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    strong_answer: Mapped[str] = mapped_column(Text)
    weak_answer: Mapped[str] = mapped_column(Text)
    basis: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="questions")


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[str | None] = mapped_column(ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)
    decision: Mapped[str] = mapped_column(String(20))  # PASS / WATCH / DILIGENCE
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="decisions")


class FounderNote(Base):
    __tablename__ = "founder_notes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    raw_notes: Mapped[str] = mapped_column(Text)
    analysis_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="founder_notes")


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    agent_provider: Mapped[str] = mapped_column(String(30))
    investment_question: Mapped[str] = mapped_column(Text, default="")
    event_found: Mapped[bool] = mapped_column(Boolean, default=False)
    event_type: Mapped[str] = mapped_column(String(50), default="NONE")
    event_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    relevance: Mapped[str] = mapped_column(Text, default="")
    claim_or_gap_affected: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str] = mapped_column(String(20), default="NO_CHANGE")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="monitoring_events")


class ResearchRun(Base):
    """Brave search + one OpenAI call. Raw results kept so every fact can be checked against its source."""

    __tablename__ = "research_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    brief: Mapped[str] = mapped_column(Text)
    queries_json: Mapped[list[str]] = mapped_column(JSON)
    results_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    facts_kept: Mapped[int] = mapped_column(Integer, default=0)
    facts_dropped: Mapped[int] = mapped_column(Integer, default=0)
    search_provider: Mapped[str] = mapped_column(String(30), default="brave")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company: Mapped[Company] = relationship(back_populates="research_runs")
