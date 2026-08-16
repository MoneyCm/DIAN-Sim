import json

import pytest

from core.study_resume import (
    NonResumableStudyRunError,
    StudyRunConflictError,
    active_elapsed_seconds,
    checkpoint_daily_run,
    clear_daily_run,
    is_resumable_practice,
    load_daily_run,
    normalize_daily_run,
    pause_daily_run,
    restore_daily_run_to_session,
    resume_daily_run,
    save_daily_run,
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
    assert payload["session_kind"] == "daily"
    assert payload["practice_mode"] == "daily"
    assert payload["run_id"]


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


def test_checkpoint_consolidates_time_and_does_not_count_later_offline_gap():
    payload = normalize_daily_run(
        {
            "session_kind": "training_recommended",
            "practice_mode": "recommended",
            "question_ids": ["q1"],
            "started_at": 100.0,
            "last_resumed_at": 100.0,
            "active_seconds": 20.0,
        }
    )
    checkpoint = checkpoint_daily_run(payload, now=140.0)
    assert checkpoint["active_seconds"] == 60.0
    assert checkpoint["last_resumed_at"] == 140.0

    recovered = dict(checkpoint, paused=True)
    assert active_elapsed_seconds(recovered, now=10_000.0) == 60.0


def test_timing_helpers_accept_zero_as_an_explicit_timestamp():
    payload = normalize_daily_run(
        {
            "question_ids": ["q1"],
            "started_at": -10.0,
            "last_resumed_at": -10.0,
            "active_seconds": 0.0,
        }
    )
    assert active_elapsed_seconds(payload, now=0.0) == 10.0
    assert checkpoint_daily_run(payload, now=0.0)["active_seconds"] == 10.0


@pytest.mark.parametrize(
    ("session_kind", "practice_mode"),
    [
        ("daily", "daily"),
        ("training_recommended", "recommended"),
        ("training_full_training", "full_training"),
        ("practice", "custom"),
        ("custom", "custom"),
    ],
)
def test_resume_policy_accepts_only_ordinary_practice(session_kind, practice_mode):
    assert is_resumable_practice(session_kind, practice_mode) is True


@pytest.mark.parametrize(
    ("session_kind", "practice_mode"),
    [
        ("diagnostic", "custom"),
        ("diagnostic_initial", "recommended"),
        ("measurement", "custom"),
        ("measurement_final", "full_training"),
        ("training_measurement", "recommended"),
        ("training_recommended", "diagnostic_transfer"),
        ("practice", "measurement"),
        ("simulation", "custom"),
    ],
)
def test_resume_policy_rejects_evidence_and_unknown_sessions(
    session_kind, practice_mode
):
    assert is_resumable_practice(session_kind, practice_mode) is False


def _resume_db():
    from db.models import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _training_payload(**overrides):
    payload = {
        "run_id": "run-training-1",
        "session_kind": "training_maximum_demand",
        "practice_mode": "maximum_demand",
        "hardcore_mode": True,
        "aids_used": True,
        "question_ids": ["q1", "q2"],
        "answers": {"q1": "B"},
        "checked_answers": {"q1": True},
        "confidences": {"q1": "unsure"},
        "error_types": {"q1": "distractor"},
        "error_reasoning": {"q1": "Confundí la excepción."},
        "question_times": {"q1": 81},
        "marked_for_review": ["q2"],
        "current_idx": 1,
        "total_time_limit": 1200,
        "started_at": 100.0,
        "active_seconds": 75.0,
        "last_resumed_at": 160.0,
        "paused": True,
    }
    payload.update(overrides)
    return payload


def test_training_round_trip_restores_mode_flags_state_and_context():
    db = _resume_db()
    try:
        saved = save_daily_run(
            db,
            41,
            _training_payload(),
            competition_id=7,
            opec_number="OPEC 236769",
        )
        loaded = load_daily_run(db, 41, competition_id=7, opec_number="236769")
        assert loaded == saved
        assert loaded["competition_id"] == 7
        assert loaded["opec_number"] == "236769"

        state = {}
        restore_daily_run_to_session(state, loaded)
        assert state["study_session_kind"] == "training_maximum_demand"
        assert state["practice_mode"] == "maximum_demand"
        assert state["hardcore_mode"] is True
        assert state["practice_aids_used"] is True
        assert state["practice_run_id"] == "run-training-1"
        assert state["current_idx"] == 1
        assert state["answers"] == {"q1": "B"}
        assert state["error_reasoning"] == {"q1": "Confundí la excepción."}
        assert state["question_times"] == {"q1": 81}
        assert state["marked_for_review"] == ["q2"]
        assert state["exam_scope"] == {
            "competition_id": 7,
            "opec_number": "236769",
        }
        # The guided-learning introduction remains a daily-only concern.
        assert state["daily_learning_complete"] is True
    finally:
        db.close()


@pytest.mark.parametrize("blocked_kind", ["diagnostic", "measurement"])
def test_evidence_sessions_cannot_be_saved_paused_resumed_or_restored(blocked_kind):
    db = _resume_db()
    payload = _training_payload(
        run_id=f"run-{blocked_kind}",
        session_kind=blocked_kind,
        practice_mode="custom",
    )
    try:
        with pytest.raises(NonResumableStudyRunError):
            save_daily_run(
                db, 52, payload, competition_id=8, opec_number="236769"
            )
        with pytest.raises(NonResumableStudyRunError):
            pause_daily_run(payload, now=200.0)
        with pytest.raises(NonResumableStudyRunError):
            resume_daily_run(payload, now=200.0)
        with pytest.raises(NonResumableStudyRunError):
            restore_daily_run_to_session({}, payload)
    finally:
        db.close()


def test_load_ignores_a_forged_measurement_checkpoint():
    from db.models import Configuration

    db = _resume_db()
    try:
        db.add(
            Configuration(
                key_name="active_daily_run:53:competition:8:opec:236769",
                value=json.dumps(
                    _training_payload(
                        session_kind="measurement", practice_mode="measurement"
                    )
                ),
            )
        )
        db.commit()
        assert load_daily_run(db, 53, 8, "236769") is None
    finally:
        db.close()


def test_compare_and_swap_prevents_stale_tab_overwrite_or_clear():
    db = _resume_db()
    try:
        first = save_daily_run(
            db,
            61,
            _training_payload(run_id="run-a"),
            competition_id=9,
            opec_number="236769",
        )
        second = save_daily_run(
            db,
            61,
            _training_payload(run_id="run-b", answers={"q1": "A"}),
            competition_id=9,
            opec_number="236769",
        )
        assert first["run_id"] == "run-a"
        assert second["run_id"] == "run-b"

        with pytest.raises(StudyRunConflictError):
            save_daily_run(
                db,
                61,
                _training_payload(run_id="run-a", answers={"q1": "C"}),
                competition_id=9,
                opec_number="236769",
                expected_run_id="run-a",
            )
        assert clear_daily_run(
            db, 61, 9, "236769", expected_run_id="run-a"
        ) is False
        assert load_daily_run(db, 61, 9, "236769")["run_id"] == "run-b"
        assert clear_daily_run(
            db, 61, 9, "236769", expected_run_id="run-b"
        ) is True
        db.commit()
        assert load_daily_run(db, 61, 9, "236769") is None
    finally:
        db.close()


def test_stale_tab_cannot_recreate_a_completed_run():
    db = _resume_db()
    try:
        saved = save_daily_run(
            db,
            62,
            _training_payload(run_id="completed-run"),
            competition_id=10,
            opec_number="236769",
        )
        assert clear_daily_run(
            db, 62, 10, "236769", expected_run_id=saved["run_id"]
        )
        db.commit()
        with pytest.raises(StudyRunConflictError):
            save_daily_run(
                db,
                62,
                saved,
                competition_id=10,
                opec_number="236769",
                expected_run_id=saved["run_id"],
            )
    finally:
        db.close()


def test_legacy_unscoped_clear_cannot_erase_a_training_run():
    db = _resume_db()
    try:
        save_daily_run(
            db,
            63,
            _training_payload(run_id="training-kept"),
            competition_id=11,
            opec_number="236769",
        )
        assert clear_daily_run(db, 63, 11, "236769") is False
        assert load_daily_run(db, 63, 11, "236769")["run_id"] == "training-kept"

        save_daily_run(
            db,
            64,
            {
                "run_id": "daily-cleared",
                "session_kind": "daily",
                "question_ids": ["q1"],
                "started_at": 100.0,
            },
            competition_id=11,
            opec_number="236769",
        )
        assert clear_daily_run(db, 64, 11, "236769") is True
    finally:
        db.close()
