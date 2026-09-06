"""
Canned LLM for UI development without an API key (LLM_PROVIDER=canned). Outputs are generic and
clearly not analysis. Never use it for the assignment demo.
"""

from __future__ import annotations

import re
from typing import TypeVar

from pydantic import BaseModel

from .llm import LLMError, render_prompt
from .llm_schemas import (
    AssessmentOutput, CriterionScore, DeckExtraction, DiligenceQuestionOut, ExtractedClaim, ExtractedFounder,
    NewEvidence, NoteAnalysis, QuestionSet,
)
from .thesis import CRITERION_KEYS

T = TypeVar("T", bound=BaseModel)
BASE_SCORES = {
    "founder_domain_fit": 4, "workflow_pain": 4, "workflow_frequency": 3, "buyer_clarity": 3,
    "customer_evidence": 2, "roi_clarity": 3, "defensibility": 2, "scalability": 3, "stage_geography_fit": 4,
}


class CannedLLM:
    name = "canned"

    def parse(self, prompt_name: str, variables: dict[str, str], schema: type[T]) -> T:
        render_prompt(prompt_name, variables)
        if schema is DeckExtraction:
            return self._extraction(variables)  # type: ignore[return-value]
        if schema is AssessmentOutput:
            return self._assessment(variables)  # type: ignore[return-value]
        if schema is QuestionSet:
            return self._questions()  # type: ignore[return-value]
        if schema is NoteAnalysis:
            return self._note(variables)  # type: ignore[return-value]
        raise LLMError(f"canned LLM has no output for {schema.__name__}")

    def _extraction(self, variables: dict[str, str]) -> DeckExtraction:
        hint = variables.get("company_hint", "Company")
        name = hint.split(" (")[0].strip() or "Company"
        pages = int(variables.get("page_count", "1") or 1)
        first_line = next((ln.strip() for ln in variables.get("deck_text", "").splitlines() if ln.strip() and not ln.startswith("===")), "")
        return DeckExtraction(
            company_name=name, website=None, stage=None, geography=None,
            founders=[ExtractedFounder(name="Founder (canned)", role="CEO", domain_background=None)],
            problem=f"[canned] First line of the deck: {first_line[:160]}" if first_line else None,
            workflow=None, customer=None, buyer=None, solution=None, business_model=None,
            traction=[], funding_ask=None,
            claims=[
                ExtractedClaim(claim=f"[canned] {name} has early customer traction", category="traction", source_page=min(3, pages),
                               supporting_text=None, evidence_strength="LOW", missing_proof="Contracts, invoices, or usage data"),
                ExtractedClaim(claim=f"[canned] {name} saves customers significant time", category="roi", source_page=min(2, pages),
                               supporting_text=None, evidence_strength="LOW", missing_proof="A measured before/after study"),
            ],
            unknowns=["This is canned output. Set OPENAI_API_KEY for real analysis."],
        )

    def _assessment(self, variables: dict[str, str]) -> AssessmentOutput:
        scores = dict(BASE_SCORES)
        has_new_evidence = variables.get("extra_context", "none").strip().lower() != "none"
        if has_new_evidence:
            scores["customer_evidence"] = 3
        return AssessmentOutput(
            criteria=[CriterionScore(key=k, score=v, reason="[canned] placeholder reason.", evidence_refs=[]) for k, v in scores.items()],
            summary="[canned] Placeholder assessment. Set OPENAI_API_KEY for a real one.",
            main_concern="[canned] No real evidence has been evaluated.",
        )

    def _questions(self) -> QuestionSet:
        return QuestionSet(questions=[
            DiligenceQuestionOut(question=f"[canned] Placeholder question {i}?", why_it_matters="Placeholder.",
                                 strong_answer="Placeholder.", weak_answer="Placeholder.", basis=CRITERION_KEYS[i - 1])
            for i in range(1, 6)
        ])

    def _note(self, variables: dict[str, str]) -> NoteAnalysis:
        notes = variables.get("notes", "").strip()
        sentence = re.split(r"(?<=[.!?])\s+", notes)[0][:200] if notes else "[canned] no notes"
        return NoteAnalysis(
            new_evidence=[NewEvidence(evidence_text=sentence, relation="SUPPORTS", claim_id=None, criterion="customer_evidence")],
            contradictions=[],
            summary="[canned] One sentence of the notes recorded as evidence.",
        )
