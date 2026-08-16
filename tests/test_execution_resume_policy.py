from pathlib import Path


EXECUTION_PAGE = (
    Path(__file__).resolve().parents[1] / "app" / "pages" / "2_Ejecucion.py"
)


def _source():
    return EXECUTION_PAGE.read_text(encoding="utf-8")


def test_execution_persists_all_resume_metadata_and_result_mode():
    source = _source()
    payload_block = source.split("def current_daily_payload", 1)[1].split(
        "def save_current_run", 1
    )[0]
    for field in (
        '"session_kind"',
        '"practice_mode"',
        '"hardcore_mode"',
        '"aids_used"',
        '"competition_id"',
        '"opec_number"',
        '"answers"',
        '"checked_answers"',
        '"current_idx"',
        '"question_times"',
        '"marked_for_review"',
    ):
        assert field in payload_block
    assert '"practice_mode": st.session_state.get(' in source
    assert '"🔖 Marcar para revisar antes de finalizar"' in source


def test_execution_uses_generic_resume_gate_but_daily_only_introduction():
    source = _source()
    assert "is_resumable_session = is_resumable_practice(" in source
    assert "if is_resumable_session and st.session_state.get(\"daily_run_paused\"" in source
    assert "if is_daily_session and not st.session_state.get(\"daily_learning_complete\"" in source
    assert "if is_daily_session:\n    st.caption(\"Paso 2 de 3" in source
    assert "if is_resumable_session:\n    elapsed = active_elapsed_seconds" in source


def test_execution_checkpoints_actions_through_compare_and_swap_helper():
    source = _source()
    # The one raw call belongs inside save_current_run; UI transitions use CAS.
    assert source.count("save_daily_run(") == 1
    assert source.count("save_current_run(") >= 10
    assert "expected_run_id=(" in source
    assert "cleared = clear_daily_run(" in source
    assert "if not cleared:" in source
    assert source.index("cleared = clear_daily_run(") < source.index(
        "update_user_stats("
    )


def test_execution_does_not_make_diagnostic_or_measurement_resumable():
    source = _source()
    assert "is_resumable_practice(session_kind, practice_mode)" in source
    non_resumable_timer = source.split(
        "if is_resumable_session:\n    elapsed = active_elapsed_seconds", 1
    )[1].split("time_left =", 1)[0]
    assert 'st.session_state.get("exam_start_time", now)' in non_resumable_timer
    assert 'st.session_state.get("active_seconds"' not in non_resumable_timer


def test_new_practice_resets_timing_and_pause_state_before_first_checkpoint():
    source = _source()
    checkpoint = source.split(
        'if st.session_state.get("_practice_resume_checkpoint") != checkpoint_id:', 1
    )[1].split('st.session_state["_practice_resume_checkpoint"]', 1)[0]
    assert 'st.session_state["active_seconds"] = 0.0' in checkpoint
    assert 'st.session_state["daily_run_paused"] = False' in checkpoint
    assert 'st.session_state["last_answer_time"] = time.time()' in checkpoint
    assert 'st.session_state.pop("practice_run_id", None)' in checkpoint


def test_interrupted_practice_is_recovered_frozen_and_checkpoints_elapsed_time():
    source = _source()
    assert 'resumed_run["paused"] = True' in source
    helper = source.split("def save_current_run", 1)[1].split(
        "render_header", 1
    )[0]
    assert "payload = checkpoint_daily_run(payload)" in helper
    assert 'st.session_state["active_seconds"] = saved["active_seconds"]' in helper
