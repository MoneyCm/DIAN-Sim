from pathlib import Path


PAGE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "pages" / "Simulacro_Real.py"
)


def _source() -> str:
    return PAGE_PATH.read_text(encoding="utf-8-sig")


def test_measurement_uses_exact_opec_policy_and_versioned_blueprint():
    source = _source()

    assert "_simulation_policy_for_scope" in source
    assert 'mode("full")' in source
    assert "target_question_count=full_mode.question_count" in source
    assert "exam_simulation_policy_version" in source
    assert "exam_blueprint_version" in source
    assert "blueprint_version=st.session_state.get" in source


def test_measurement_is_not_shortened_by_subscription_tier():
    source = _source()

    assert "máximo 2 casos" not in source
    assert "Ver opciones de entrenamiento PRO" not in source
    assert "AuthManager.is_pro" not in source


def test_timer_and_navigation_come_from_versioned_internal_policy():
    source = _source()

    assert 'st.session_state.get("exam_minutes_per_question", 2.0)' in source
    assert 'st.session_state.get("exam_navigation_mode", "sequential")' in source
    assert "Cantidad y duración oficiales: pendientes de publicación" in source


def test_measurement_can_mark_items_without_changing_the_score():
    source = _source()

    assert '"🔖 Marcar para revisión"' in source
    assert '"marked_for_review": list(' in source
    assert "pregunta(s) para revisión posterior" in source
