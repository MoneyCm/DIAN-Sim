from core.study_resume import normalize_daily_run, restore_daily_run_to_session


def test_daily_run_normalizes_and_clamps_position():
    payload = normalize_daily_run({
        "question_ids": ["q1", "q2"],
        "answers": {"q1": "A"},
        "checked_answers": {"q1": True, "q2": False},
        "confidences": {"q1": "confident", "q2": "invalid"},
        "error_types": {"q1": "mala_interpretacion"},
        "current_idx": 99,
        "total_time_limit": 10,
        "started_at": 100.0,
    })
    assert payload["current_idx"] == 1
    assert payload["total_time_limit"] == 60
    assert payload["checked_answers"] == {"q1": True}
    assert payload["confidences"] == {"q1": "confident"}
    assert payload["error_types"] == {"q1": "mala_interpretacion"}


def test_daily_run_restores_execution_state():
    state = {}
    payload = normalize_daily_run({
        "question_ids": ["q1", "q2"], "answers": {"q1": "B"},
        "checked_answers": {"q1": True}, "current_idx": 1,
        "confidences": {"q1": "unsure"}, "error_types": {"q1": "distractor"},
        "total_time_limit": 1800, "started_at": 100.0,
        "learning_complete": True, "learning_minutes": 8,
    })
    restore_daily_run_to_session(state, payload)
    assert state["exam_mode"] is True
    assert state["study_session_kind"] == "daily"
    assert state["current_idx"] == 1
    assert state["answers"] == {"q1": "B"}
    assert state["confidences"] == {"q1": "unsure"}
    assert state["error_types"] == {"q1": "distractor"}
    assert state["daily_learning_complete"] is True
    assert state["daily_learning_minutes"] == 8
