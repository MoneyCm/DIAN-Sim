from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core.spaced_repetition import is_review_due, schedule_review


def performance(**overrides):
    values = {
        "review_interval_days": 0.0,
        "ease_factor": 2.5,
        "review_count": 0,
        "lapse_count": 0,
        "misses": 0,
        "is_mastered": False,
        "next_review": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_first_confident_answer_schedules_four_days():
    now = datetime(2026, 7, 27, 10, 0)
    item = performance()

    result = schedule_review(item, True, "confident", now=now)

    assert result.interval_days == 4
    assert result.next_review == now + timedelta(days=4)
    assert item.last_confidence == "confident"
    assert item.last_error_type is None


def test_recurrent_correct_answer_expands_interval():
    now = datetime(2026, 7, 27, 10, 0)
    item = performance(review_interval_days=4, review_count=2, ease_factor=2.5)

    result = schedule_review(item, True, "confident", now=now)

    assert result.interval_days > 10
    assert result.ease_factor > 2.5


def test_incorrect_answer_resets_interval_and_records_cause():
    now = datetime(2026, 7, 27, 10, 0)
    item = performance(review_interval_days=20, review_count=4, is_mastered=True)

    result = schedule_review(
        item,
        False,
        "guess",
        error_type="confusion_conceptual",
        now=now,
    )

    assert result.interval_days == 1
    assert result.lapse_count == 1
    assert item.last_error_type == "confusion_conceptual"
    assert item.is_mastered is False


def test_legacy_error_without_date_is_due():
    assert is_review_due(performance(misses=1)) is True
    assert is_review_due(performance(misses=0)) is False


def test_future_review_is_not_due():
    now = datetime(2026, 7, 27, 10, 0)
    item = performance(next_review=now + timedelta(days=1))
    assert is_review_due(item, now=now) is False


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValueError):
        schedule_review(performance(), True, "maximum")