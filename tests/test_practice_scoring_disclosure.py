from core.gamification import (
    PRACTICE_SCORING_DISCLOSURE,
    PRACTICE_SCORING_STATUS,
    PRACTICE_TRACK_WEIGHTS,
    calculate_practice_index,
)


def test_practice_index_preserves_internal_gamification_behavior():
    index, meets_functional_goal = calculate_practice_index({
        "FUNCIONAL": (8, 10),
        "COMPORTAMENTAL": (5, 10),
        "INTEGRIDAD": (5, 10),
    })

    assert PRACTICE_TRACK_WEIGHTS == {
        "FUNCIONAL": 60,
        "COMPORTAMENTAL": 20,
        "INTEGRIDAD": 20,
    }
    assert index == 68.0
    assert meets_functional_goal is True


def test_functional_goal_is_training_state_not_official_opec_result():
    _, meets_functional_goal = calculate_practice_index({
        "FUNCIONAL": (6, 10),
        "COMPORTAMENTAL": (10, 10),
        "INTEGRIDAD": (10, 10),
    })

    assert meets_functional_goal is False
    assert PRACTICE_SCORING_STATUS == "provisional_editable_not_official_exam_weighting"
    assert "índice interno" in PRACTICE_SCORING_DISCLOSURE.lower()
    assert "no equivale" in PRACTICE_SCORING_DISCLOSURE.lower()
    assert "modalidad en simo" in PRACTICE_SCORING_DISCLOSURE.lower()
