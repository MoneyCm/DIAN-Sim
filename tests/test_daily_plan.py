from datetime import datetime, timedelta
from types import SimpleNamespace

from core.adaptive import build_daily_plan, select_daily_questions


def question(qid, topic="Tema", difficulty=2):
    return SimpleNamespace(
        question_id=qid,
        track="FUNCIONAL",
        competency="Competencia",
        topic=topic,
        difficulty=difficulty,
    )


def skill(topic, mastery, priority=1.0):
    return SimpleNamespace(
        track="FUNCIONAL",
        competency="Competencia",
        topic=topic,
        mastery_score=mastery,
        priority_weight=priority,
    )


def performance(hits, misses, last_attempt):
    return SimpleNamespace(hits=hits, misses=misses, last_attempt=last_attempt)


def test_daily_plan_prioritizes_weak_recurrent_errors():
    now = datetime(2026, 7, 26, 12, 0)
    weak = question("weak", "Débil")
    strong = question("strong", "Fuerte")
    skills = {
        (weak.track, weak.competency, weak.topic): skill("Débil", 20, 5),
        (strong.track, strong.competency, strong.topic): skill("Fuerte", 95, 1),
    }
    performances = {
        "weak": performance(1, 5, now - timedelta(days=10)),
        "strong": performance(8, 0, now - timedelta(days=1)),
    }

    plan = build_daily_plan([strong, weak], skills, performances, n=2, now=now)

    assert plan[0].question.question_id == "weak"
    assert "dominio bajo" in plan[0].reasons
    assert "errores recurrentes" in plan[0].reasons


def test_daily_plan_prioritizes_overdue_review_when_mastery_matches():
    now = datetime(2026, 7, 26, 12, 0)
    recent = question("recent", "Reciente")
    overdue = question("overdue", "Pendiente")
    skills = {
        (recent.track, recent.competency, recent.topic): skill("Reciente", 60),
        (overdue.track, overdue.competency, overdue.topic): skill("Pendiente", 60),
    }
    performances = {
        "recent": performance(2, 2, now - timedelta(hours=12)),
        "overdue": performance(2, 2, now - timedelta(days=20)),
    }

    selected = select_daily_questions([recent, overdue], skills, performances, n=1, now=now)
    assert selected[0].question_id == "overdue"


def test_daily_plan_preserves_topic_variety():
    now = datetime(2026, 7, 26, 12, 0)
    questions = [question(f"a{i}", "A") for i in range(8)]
    questions += [question(f"b{i}", "B") for i in range(4)]
    questions += [question(f"c{i}", "C") for i in range(4)]
    skills = {
        ("FUNCIONAL", "Competencia", "A"): skill("A", 5, 7),
        ("FUNCIONAL", "Competencia", "B"): skill("B", 30, 3),
        ("FUNCIONAL", "Competencia", "C"): skill("C", 30, 3),
    }

    selected = select_daily_questions(questions, skills, {}, n=10, now=now)
    topics = [item.topic for item in selected]

    assert topics.count("A") <= 4
    assert {"A", "B", "C"}.issubset(set(topics))


def test_daily_plan_handles_empty_or_zero_size():
    assert build_daily_plan([], {}, {}, n=20) == []
    assert build_daily_plan([question("q")], {}, {}, n=0) == []