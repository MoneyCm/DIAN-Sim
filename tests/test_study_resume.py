from core.study_resume import (
    active_elapsed_seconds,
    normalize_daily_run,
    pause_daily_run,
    restore_daily_run_to_session,
    resume_daily_run,
)


def test_result_payload_round_trip(tmp_path):
    """La serialización del resultado conserva listas, métricas y desglose."""
    from core.session_results import load_last_result, load_result_history, save_last_result
    from db.models import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path / 'results.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    payload = {
        "session_kind": "daily", "total": 5, "correct": 4,
        "q_ids": ["q1", "q2"], "breakdown": {"FUNCIONAL": [4, 5]},
    }
    save_last_result(db, 77, payload)
    db.commit()
    restored = load_last_result(db, 77)
    assert {key: restored[key] for key in payload} == payload
    assert restored["saved_at"]
    history = load_result_history(db, 77)
    assert len(history) == 1
    assert history[0]["session_kind"] == "daily"
    db.close()


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


def test_pause_freezes_active_time_and_resume_continues_from_accumulator():
    payload = normalize_daily_run({
        "question_ids": ["q1"], "started_at": 100.0,
        "last_resumed_at": 100.0, "active_seconds": 20.0,
    })
    paused = pause_daily_run(payload, now=140.0)
    assert paused["paused"] is True
    assert paused["active_seconds"] == 60.0
    assert active_elapsed_seconds(paused, now=999.0) == 60.0

    resumed = resume_daily_run(paused, now=200.0)
    assert resumed["paused"] is False
    assert active_elapsed_seconds(resumed, now=230.0) == 90.0
