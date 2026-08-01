from core.motivation import build_weekly_progress, coverage_percent, topic_status


def test_weekly_goal_is_flexible_and_capped_at_five_days():
    progress = build_weekly_progress(completed_days=3, configured_days=6)

    assert progress.target_days == 5
    assert progress.remaining_days == 2
    assert progress.ratio == 0.6
    assert not progress.is_complete


def test_weekly_goal_completes_without_requiring_perfection():
    progress = build_weekly_progress(completed_days=5, configured_days=6)

    assert progress.is_complete
    assert progress.ratio == 1.0


def test_coverage_is_bounded():
    assert coverage_percent(10, 4) == 40.0
    assert coverage_percent(0, 0) == 0.0
    assert coverage_percent(2, 3) == 100.0


def test_topic_status_requires_practice_before_mastery():
    assert topic_status(90, 0) == ("Pendiente", "⚪")
    assert topic_status(40, 2) == ("Reforzar", "🔴")
    assert topic_status(60, 3) == ("En práctica", "🟡")
    assert topic_status(80, 4) == ("Consolidando", "🔵")
    assert topic_status(90, 5) == ("Dominado", "🟢")