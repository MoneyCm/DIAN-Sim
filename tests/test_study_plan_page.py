from pathlib import Path


SOURCE = Path("app/pages/11_Plan_Estudio.py").read_text(encoding="utf-8")


def test_plan_is_scoped_to_the_active_user_competition_and_opec():
    assert "user_opec_id=active_opec.id" in SOURCE
    assert "competition_id=active_opec.competition_id" in SOURCE
    assert 'bank_partitions=("training",)' in SOURCE
    assert "StudyPlanConfig" not in SOURCE


def test_plan_discloses_internal_target_and_never_promises_a_result():
    assert "Objetivo interno de precisión" in SOURCE
    assert "ni garantiza un resultado" in SOURCE
    assert "puntaje oficial" in SOURCE


def test_daily_mission_persists_explainable_actions_and_source_locator_safely():
    assert "StudyActivity(" in SOURCE
    assert "mission.reason" in SOURCE
    assert "mission.source.locator_verified" in SOURCE
    assert "no se presenta un artículo o página inventados" in SOURCE


def test_activity_can_be_completed_or_deferred_but_not_faked_as_completed():
    assert 'activity.status = "completed"' in SOURCE
    assert "activity.completed_at = utc_now()" in SOURCE
    assert 'activity.status = "deferred"' in SOURCE
