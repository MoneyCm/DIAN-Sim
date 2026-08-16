from __future__ import annotations

import pytest

from core.learning.difficulty import (
    DIFFICULTY_RUBRIC,
    DifficultyPolicy,
    TopicDifficultyEvidence,
    difficulty_label,
    difficulty_rubric,
    legacy_difficulty_to_editorial,
    mastery_difficulty,
    normalize_difficulty,
    target_difficulty,
)


def evidence(**overrides) -> TopicDifficultyEvidence:
    values = {
        "mastery": 85.0,
        "current_difficulty": 5,
        "total_attempts": 14,
        "new_attempts": 4,
        "new_correct": 4,
        "delayed_retention_attempts": 3,
        "delayed_retention_correct": 3,
        "measurement_attempts": 3,
        "measurement_correct": 3,
        "lapses": 0,
        "slow_response_ratio": 0.0,
        "low_confidence_ratio": 0.0,
    }
    values.update(overrides)
    return TopicDifficultyEvidence(**values)


@pytest.mark.parametrize("legacy,expected", [(1, 2), (2, 5), (3, 8)])
def test_legacy_mapping_is_explicit_and_normalized_output_is_idempotent(legacy, expected):
    normalized = legacy_difficulty_to_editorial(legacy)

    assert normalized == expected
    assert normalize_difficulty(normalized) == normalized
    assert legacy_difficulty_to_editorial(normalized) is normalized


@pytest.mark.parametrize("value", [0, 4, 11, 1.0, True])
def test_legacy_mapping_rejects_values_outside_declared_scale(value):
    with pytest.raises(ValueError):
        normalize_difficulty(value, source_scale="legacy")


def test_editorial_rubric_covers_all_ten_stable_labels():
    assert [item.score for item in DIFFICULTY_RUBRIC] == list(range(1, 11))
    assert len({item.label for item in DIFFICULTY_RUBRIC}) == 10
    for score in range(1, 11):
        assert difficulty_label(score) == difficulty_rubric(score).label
        assert difficulty_rubric(score).description


@pytest.mark.parametrize(
    "mastery,expected",
    [(0, 1), (9.999, 1), (10, 2), (49.9, 5), (50, 6), (89.9, 9), (90, 10), (100, 10)],
)
def test_mastery_mapping_has_explicit_boundaries(mastery, expected):
    assert mastery_difficulty(mastery) == expected


@pytest.mark.parametrize("mastery", [-0.01, 100.01, float("inf"), float("nan")])
def test_mastery_outside_canonical_range_is_rejected(mastery):
    with pytest.raises(ValueError):
        mastery_difficulty(mastery)


def test_insufficient_samples_never_promote_even_with_perfect_mastery():
    result = target_difficulty(
        evidence(
            mastery=100,
            current_difficulty=2,
            total_attempts=7,
            new_attempts=3,
            new_correct=3,
            delayed_retention_attempts=2,
            delayed_retention_correct=2,
            measurement_attempts=2,
            measurement_correct=2,
        )
    )

    assert result.target == 2
    assert result.evidence_sufficient is False
    assert result.promotion_eligible is False


def test_robust_evidence_promotes_only_one_editorial_step():
    result = target_difficulty(evidence())

    assert result.mastery_target == 9
    assert result.target == 6
    assert result.evidence_sufficient is True
    assert result.promotion_eligible is True


@pytest.mark.parametrize(
    "weak_signal",
    [
        {"new_attempts": 4, "new_correct": 2},
        {"delayed_retention_attempts": 3, "delayed_retention_correct": 1},
        {"measurement_attempts": 3, "measurement_correct": 1},
    ],
)
def test_each_independent_accuracy_signal_can_reduce_target(weak_signal):
    result = target_difficulty(evidence(**weak_signal))

    assert result.target == 4
    assert result.promotion_eligible is False


def test_lapses_reduce_target_and_block_promotion():
    result = target_difficulty(evidence(lapses=4))

    assert result.target == 3
    assert result.promotion_eligible is False
    assert any("lapsos" in reason for reason in result.reasons)


def test_time_and_confidence_change_priority_but_never_lower_target():
    baseline = target_difficulty(evidence())
    friction = target_difficulty(
        evidence(slow_response_ratio=1.0, low_confidence_ratio=1.0)
    )

    assert friction.target == baseline.target
    assert friction.mastery_target == baseline.mastery_target
    assert friction.priority > baseline.priority
    assert any("tiempo/confianza" in reason for reason in friction.reasons)


def test_decision_is_stable_for_identical_evidence():
    item = evidence(mastery=73, current_difficulty=6)

    assert target_difficulty(item) == target_difficulty(item)


@pytest.mark.parametrize(
    "values",
    [
        {"new_attempts": 1, "new_correct": 2},
        {"delayed_retention_attempts": -1},
        {"measurement_attempts": 1, "measurement_correct": 2},
        {"lapses": -1},
        {"current_difficulty": 11},
        {"slow_response_ratio": 1.01},
        {"low_confidence_ratio": -0.01},
    ],
)
def test_invalid_evidence_is_rejected(values):
    with pytest.raises(ValueError):
        evidence(**values)


def test_policy_rejects_incoherent_thresholds():
    with pytest.raises(ValueError):
        DifficultyPolicy(weak_accuracy=0.3, very_weak_accuracy=0.4)
