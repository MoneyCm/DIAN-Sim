from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core.learning.engine import schedule_next_review
from core.learning.review_policy import normalize_confidence, review_interval
from core.spaced_repetition import schedule_review


NOW = datetime(2026, 8, 15, 9, 0)


def _performance(**overrides):
    values = {
        "review_interval_days": 0.0,
        "ease_factor": 2.5,
        "review_count": 0,
        "lapse_count": 0,
        "is_mastered": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_confidence_aliases_and_missing_are_explicit():
    assert normalize_confidence("guess") == "low"
    assert normalize_confidence("unsure") == "medium"
    assert normalize_confidence("confident") == "high"
    assert normalize_confidence(None) is None
    with pytest.raises(ValueError):
        normalize_confidence("certain")


def test_high_confidence_error_is_due_before_other_errors():
    high = review_interval(result="incorrect", confidence="high")
    medium = review_interval(result="incorrect", confidence="medium")
    low = review_interval(result="incorrect", confidence="low")
    assert high.interval_days <= medium.interval_days <= low.interval_days


def test_correct_confidence_order_is_monotonic():
    low = review_interval(result="correct", confidence="low")
    medium = review_interval(result="correct", confidence="medium")
    high = review_interval(result="correct", confidence="high")
    assert low.interval_days <= medium.interval_days <= high.interval_days


def test_both_public_schedulers_use_the_same_internal_policy():
    item = _performance()
    legacy = schedule_review(item, False, "confident", now=NOW)
    topic = schedule_next_review("incorrect", "high", 99, now=NOW)
    assert legacy.interval_days == 0.25
    assert legacy.next_review == topic == NOW + timedelta(days=0.25)


def test_interval_does_not_mark_mastery():
    item = _performance(
        review_interval_days=20,
        review_count=5,
        ease_factor=3.0,
        is_mastered=False,
    )
    outcome = schedule_review(item, True, "confident", now=NOW)
    assert outcome.interval_days >= 30
    assert item.is_mastered is False


def test_mastery_argument_does_not_change_review_date():
    weak = schedule_next_review("correct", "medium", 5, now=NOW)
    strong = schedule_next_review("correct", "medium", 95, now=NOW)
    assert weak == strong
