from pathlib import Path


SOURCE = Path("app/pages/6_Dashboard.py").read_text(encoding="utf-8")


def test_dashboard_defaults_to_fast_action_summary():
    assert 'st.subheader("Tu foco inmediato")' in SOURCE
    assert '"Debilidad prioritaria"' in SOURCE
    assert '"Repasos vencidos"' in SOURCE
    assert '"Documentos pendientes"' in SOURCE
    assert '"Última medición"' in SOURCE
    assert '"Ver análisis avanzado, calendario y exportaciones"' in SOURCE
    assert "if not show_advanced_dashboard:" in SOURCE
    assert "st.stop()" in SOURCE


def test_dashboard_summary_uses_canonical_opec_scoped_evidence():
    assert "OpecTopicState" in SOURCE
    assert "ErrorEpisode" in SOURCE
    assert "OpecLearningSession" in SOURCE
    assert "user_opec_id=active_opec.id" in SOURCE
    assert "build_study_library(active_opec.opec_number)" in SOURCE


def test_legacy_plan_no_longer_drives_the_dashboard():
    assert "StudyPlanConfig" not in SOURCE
    assert "study_config.weekday_minutes" in SOURCE
