"""Exactly five decision-changing diligence questions (BUILD_SPEC §8). Count enforced in code."""

from __future__ import annotations

import json

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..llm import LLMClient, LLMError
from ..llm_schemas import QuestionSet
from ..models import Assessment, Company, DiligenceQuestion
from .analysis import AnalysisError, claims_block, latest_assessment, snapshot_json

REQUIRED_COUNT = 5


def _assessment_block(assessment: Assessment) -> str:
    return json.dumps(assessment.criterion_scores_json, indent=2, ensure_ascii=False)


def generate_questions(db: Session, company: Company, llm: LLMClient) -> list[DiligenceQuestion]:
    assessment = latest_assessment(db, company.id)
    if assessment is None:
        raise AnalysisError("Run the deck analysis before generating questions.")
    variables = {
        "snapshot": snapshot_json(company),
        "claims_block": claims_block(db, company.id),
        "assessment_block": _assessment_block(assessment),
        "main_concern": assessment.main_concern or "(none stated)",
        "feedback": "",
    }
    output = llm.parse("questions", variables, QuestionSet)
    if len(output.questions) != REQUIRED_COUNT:
        variables["feedback"] = (
            f"\nYour previous response contained {len(output.questions)} questions. "
            f"Return exactly {REQUIRED_COUNT}."
        )
        output = llm.parse("questions", variables, QuestionSet)
    if len(output.questions) != REQUIRED_COUNT:
        raise LLMError(f"Model returned {len(output.questions)} questions; exactly {REQUIRED_COUNT} required.")

    db.execute(delete(DiligenceQuestion).where(DiligenceQuestion.assessment_id == assessment.id))
    rows: list[DiligenceQuestion] = []
    for position, item in enumerate(output.questions, start=1):
        row = DiligenceQuestion(
            company_id=company.id,
            assessment_id=assessment.id,
            position=position,
            question=item.question,
            why_it_matters=item.why_it_matters,
            strong_answer=item.strong_answer,
            weak_answer=item.weak_answer,
            basis=item.basis,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    return rows
