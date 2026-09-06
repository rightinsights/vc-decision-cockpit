"""Thesis scoring. Pure functions; the LLM never computes the total (BUILD_SPEC §7)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from .thesis import CRITERION_KEYS, LABELS, WEIGHTS, Recommendation, band


class ScoreResult(TypedDict):
    overall: int | None
    used_weight: int


class CriterionDelta(TypedDict):
    key: str
    label: str
    old: int | None
    new: int | None
    reason: str


def compute_overall(scores: Mapping[str, int | None]) -> ScoreResult:
    """
    normalized = (score - 1) / 4 ; weighted = normalized * weight ; overall = sum(weighted)
    Null criteria are excluded and the total is rescaled over the weights actually used.
    """
    used = [(key, WEIGHTS[key]) for key in CRITERION_KEYS if scores.get(key) is not None]
    used_weight = sum(weight for _, weight in used)
    if used_weight == 0:
        return {"overall": None, "used_weight": 0}
    weighted = 0.0
    for key, weight in used:
        raw = scores[key]
        if not 1 <= raw <= 5:
            raise ValueError(f"criterion {key} score {raw} outside 1..5")
        weighted += (raw - 1) / 4 * weight
    overall = round(weighted / used_weight * 100)
    return {"overall": overall, "used_weight": used_weight}


def recommend(overall: int | None) -> Recommendation | None:
    if overall is None:
        return None
    return band(overall)


def diff_scores(old: Mapping[str, Any], new: Mapping[str, Any]) -> list[CriterionDelta]:
    """Return only the criteria whose score changed. Each value is {score, reason, ...}."""
    deltas: list[CriterionDelta] = []
    for key in CRITERION_KEYS:
        old_score = (old.get(key) or {}).get("score")
        new_score = (new.get(key) or {}).get("score")
        if old_score != new_score:
            deltas.append({
                "key": key,
                "label": LABELS[key],
                "old": old_score,
                "new": new_score,
                "reason": (new.get(key) or {}).get("reason", ""),
            })
    return deltas
