from dataclasses import dataclass

from core.practice_modes import (
    MODE_ERRORS,
    MODE_FULL,
    MODE_MAXIMUM,
    MODE_RECOMMENDED,
    select_practice_questions,
)


@dataclass
class Question:
    question_id: str
    case_id: str
    topic: str
    competency: str = "Fiscalización"
    difficulty: int = 5
    track: str = "FUNCIONAL"
    question_type: str = "SITUATIONAL"
    quality_report: dict | None = None


def _questions(case_count=5, difficulty=5):
    result = []
    for case_number in range(1, case_count + 1):
        for prompt in range(1, 4):
            result.append(
                Question(
                    question_id=f"q{case_number}-{prompt}",
                    case_id=f"c{case_number}",
                    topic=f"OPEC 236769 · Función {(case_number - 1) % 9 + 1}",
                    difficulty=difficulty,
                    quality_report={"opec_number": "236769", "function_number": (case_number - 1) % 9 + 1},
                )
            )
    return result


def test_recommended_prioritises_unseen_and_respects_repeat_ceiling():
    questions = _questions(2)
    counts = {"q1-1": 3, "q1-2": 2}
    result = select_practice_questions(
        questions,
        mode=MODE_RECOMMENDED,
        requested_count=4,
        opec_number="236769",
        exposure_counts=counts,
        max_exposures=3,
    )
    ids = [question.question_id for question in result.questions]
    assert "q1-1" not in ids
    assert "q1-2" not in ids[:3]
    assert result.complete is True


def test_full_training_preserves_complete_case_groups():
    result = select_practice_questions(
        _questions(4),
        mode=MODE_FULL,
        requested_count=9,
        opec_number="236769",
    )
    case_counts = {}
    for question in result.questions:
        case_counts[question.case_id] = case_counts.get(question.case_id, 0) + 1
    assert result.complete is True
    assert set(case_counts.values()) == {3}


def test_full_training_does_not_claim_complete_when_bank_is_short():
    result = select_practice_questions(
        _questions(2),
        mode=MODE_FULL,
        requested_count=9,
        opec_number="236769",
    )
    assert result.complete is False
    assert len(result.questions) == 6


def test_error_transfer_uses_related_but_different_questions():
    questions = _questions(2)
    result = select_practice_questions(
        questions,
        mode=MODE_ERRORS,
        requested_count=2,
        opec_number="236769",
        error_question_ids={"q1-1"},
        error_topic_ids={questions[0].topic},
    )
    assert result.complete is True
    assert "q1-1" not in {question.question_id for question in result.questions}
    assert all(question.topic == questions[0].topic for question in result.questions)


def test_maximum_demand_requires_level_8_and_complete_case_groups():
    questions = _questions(2, difficulty=8) + _questions(1, difficulty=7)
    # Avoid duplicate IDs from the low-difficulty helper.
    for question in questions[6:]:
        question.question_id = "low-" + question.question_id
        question.case_id = "low-" + question.case_id
    result = select_practice_questions(
        questions,
        mode=MODE_MAXIMUM,
        requested_count=6,
        opec_number="236769",
    )
    assert result.complete is True
    assert all(question.difficulty >= 8 for question in result.questions)
    assert result.aids_allowed is False


def test_invalid_mode_and_exposure_limit_fail_closed():
    import pytest

    with pytest.raises(ValueError):
        select_practice_questions(
            _questions(), mode="official_exam", requested_count=5, opec_number="236769"
        )
    with pytest.raises(ValueError):
        select_practice_questions(
            _questions(), mode=MODE_RECOMMENDED, requested_count=5,
            opec_number="236769", max_exposures=0,
        )
