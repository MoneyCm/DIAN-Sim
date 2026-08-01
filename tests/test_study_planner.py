import datetime

from core.study_planner import build_timed_session, days_until_exam, preparation_phase


def test_thirty_minute_session_matches_recommended_structure():
    session = build_timed_session(30)

    assert session.total_minutes == 30
    assert session.review_minutes == 5
    assert session.learning_minutes == 12
    assert session.practice_minutes == 10
    assert session.closing_minutes == 3
    assert session.question_goal == 5


def test_session_minutes_always_add_up():
    for minutes in (15, 30, 45, 60, 90, 180):
        session = build_timed_session(minutes)
        assert (
            session.review_minutes
            + session.learning_minutes
            + session.practice_minutes
            + session.closing_minutes
            == session.total_minutes
        )


def test_days_until_exam_never_returns_negative_value():
    today = datetime.date(2026, 8, 1)

    assert days_until_exam(datetime.date(2026, 12, 15), today) == 136
    assert days_until_exam(datetime.date(2026, 7, 1), today) == 0
    assert days_until_exam(None, today) is None


def test_preparation_phase_changes_near_exam():
    assert preparation_phase(None) == "Fecha pendiente"
    assert preparation_phase(100) == "Cobertura del temario"
    assert preparation_phase(70) == "Integración y casos"
    assert preparation_phase(30) == "Simulacros y corrección"
    assert preparation_phase(10) == "Repaso final"