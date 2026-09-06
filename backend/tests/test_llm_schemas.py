import pytest
from pydantic import ValidationError

from app.llm_schemas import (
    AssessmentOutput,
    CriterionScore,
    DeckExtraction,
    QuestionSet,
    normalize_criteria,
)
from app.thesis import CRITERION_KEYS


def test_criterion_score_rejects_out_of_range():
    with pytest.raises(ValidationError):
        CriterionScore(key="workflow_pain", score=6, reason="x", evidence_refs=[])
    assert CriterionScore(key="workflow_pain", score=None, reason="x", evidence_refs=[]).score is None


def test_normalize_fills_missing_keys_with_null():
    output = AssessmentOutput(
        criteria=[CriterionScore(key="workflow_pain", score=4, reason="painful", evidence_refs=["p3"])],
        summary="s", main_concern="c",
    )
    scores = normalize_criteria(output)
    assert list(scores) == CRITERION_KEYS
    assert scores["workflow_pain"] == {"score": 4, "reason": "painful", "evidence_refs": ["p3"]}
    assert scores["customer_evidence"]["score"] is None


def _assert_strict(schema: dict):
    """Strict structured outputs: additionalProperties false and all properties required, recursively."""
    if schema.get("type") == "object":
        assert schema.get("additionalProperties") is False, schema
        props = schema.get("properties", {})
        assert set(schema.get("required", [])) == set(props), schema
        for sub in props.values():
            _assert_strict(sub)
    for sub in schema.get("$defs", {}).values():
        _assert_strict(sub)
    for sub in schema.get("anyOf", []):
        _assert_strict(sub)
    if "items" in schema:
        _assert_strict(schema["items"])


@pytest.mark.parametrize("model", [DeckExtraction, AssessmentOutput, QuestionSet])
def test_llm_schemas_are_strict_compatible(model):
    _assert_strict(model.model_json_schema())
