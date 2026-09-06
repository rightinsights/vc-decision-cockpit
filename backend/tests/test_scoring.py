import pytest

from app.scoring import compute_overall, diff_scores, recommend
from app.thesis import CRITERION_KEYS, WEIGHTS


def all_scores(value):
    return {key: value for key in CRITERION_KEYS}


def test_weights_sum_to_100():
    assert sum(WEIGHTS.values()) == 100


def test_all_fives_is_100():
    assert compute_overall(all_scores(5)) == {"overall": 100, "used_weight": 100}


def test_all_ones_is_0():
    assert compute_overall(all_scores(1)) == {"overall": 0, "used_weight": 100}


def test_all_threes_is_50():
    assert compute_overall(all_scores(3))["overall"] == 50


def test_null_criterion_excluded_and_rescaled():
    scores = all_scores(3)
    scores["customer_evidence"] = None
    result = compute_overall(scores)
    assert result["used_weight"] == 90
    assert result["overall"] == 50  # all remaining are 3 -> still 50 after rescale


def test_null_rescale_changes_total_when_others_differ():
    scores = all_scores(5)
    scores["defensibility"] = 1  # weight 15 -> contributes 0
    assert compute_overall(scores)["overall"] == 85
    scores["defensibility"] = None  # excluded: remaining are all 5 -> 100
    assert compute_overall(scores)["overall"] == 100


def test_all_null_gives_none():
    assert compute_overall(all_scores(None)) == {"overall": None, "used_weight": 0}
    assert recommend(None) is None


def test_out_of_range_raises():
    scores = all_scores(3)
    scores["workflow_pain"] = 6
    with pytest.raises(ValueError):
        compute_overall(scores)


@pytest.mark.parametrize(
    "overall,expected",
    [(0, "PASS"), (49, "PASS"), (50, "WATCH"), (69, "WATCH"), (70, "DILIGENCE"), (100, "DILIGENCE")],
)
def test_bands(overall, expected):
    assert recommend(overall) == expected


def test_diff_scores_reports_only_changes():
    old = {k: {"score": 3, "reason": "old"} for k in CRITERION_KEYS}
    new = {k: {"score": 3, "reason": "same"} for k in CRITERION_KEYS}
    new["customer_evidence"] = {"score": 4, "reason": "two paid pilots confirmed"}
    new["roi_clarity"] = {"score": None, "reason": "unknown now"}
    deltas = diff_scores(old, new)
    assert [d["key"] for d in deltas] == ["customer_evidence", "roi_clarity"]
    assert deltas[0] == {
        "key": "customer_evidence", "label": "Customer evidence",
        "old": 3, "new": 4, "reason": "two paid pilots confirmed",
    }
