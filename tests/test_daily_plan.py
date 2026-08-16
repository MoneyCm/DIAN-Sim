from datetime import datetime, timedelta
from types import SimpleNamespace

from core.adaptive import (
    build_daily_plan,
    build_hybrid_remaining_daily_plan,
    build_remaining_daily_plan,
    build_study_plan_stage,
    count_topics_requiring_diagnosis,
    select_daily_questions,
)


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

def test_remaining_daily_plan_excludes_completed_questions():
    now = datetime(2026, 7, 27, 12, 0)
    questions = [question(f"q{i}", f"Tema {i}") for i in range(6)]

    plan = build_remaining_daily_plan(
        questions,
        {},
        {},
        completed_question_ids={"q0", "q1"},
        daily_goal=5,
        now=now,
    )

    assert len(plan) == 3
    assert {item.question.question_id for item in plan}.isdisjoint({"q0", "q1"})


def test_remaining_daily_plan_stops_at_completed_goal():
    questions = [question(f"q{i}") for i in range(3)]
    plan = build_remaining_daily_plan(
        questions,
        {},
        {},
        completed_question_ids={"a", "b", "c"},
        daily_goal=3,
    )
    assert plan == []


def test_hybrid_daily_plan_includes_complete_official_cases():
    official_questions = [question(f"official-{i}", "Normativa") for i in range(6)]
    for index, item in enumerate(official_questions):
        item.options_json = {"A": "Uno", "B": "Dos", "C": "Tres"}
        item.correct_key = "A"
        item.question_type = "SITUATIONAL"
        item.stem = f"Pregunta {index}"
        item.is_verified = True
        item.quality_report = {"status": "APPROVED", "review": "human_source_grounded"}
        item.created_at = str(index).zfill(2)
    cases = []
    for case_index in range(2):
        group = official_questions[case_index * 3:(case_index + 1) * 3]
        case = SimpleNamespace(id=f"case-{case_index}", text="Caso laboral", questions=group)
        cases.append(case)
        for item in group:
            item.case_study = case

    individual = [question(f"practice-{i}", "Refuerzo") for i in range(4)]
    for item in individual:
        item.case_study = None
    established_performance = {
        item.question_id: performance(3, 0, datetime(2026, 8, 1, 12, 0))
        for item in official_questions + individual
    }
    plan = build_hybrid_remaining_daily_plan(
        official_questions + individual, {}, established_performance, set(), daily_goal=8, max_official_cases=2
    )
    selected_ids = {item.question.question_id for item in plan}

    assert len(plan) == 8
    assert all(question.question_id in selected_ids for question in official_questions)
    assert sum("caso PJS de práctica" in item.reasons for item in plan) == 6


def test_hybrid_daily_plan_reserves_slots_for_unmeasured_topics():
    now = datetime(2026, 8, 2, 12, 0)
    new_topics = [question("new-a", "A"), question("new-b", "B"), question("new-c", "C")]
    repeated_weakness = [question(f"weak-{index}", "Debilidad") for index in range(5)]
    performances = {
        item.question_id: performance(0, 4, now - timedelta(days=2))
        for item in repeated_weakness
    }

    plan = build_hybrid_remaining_daily_plan(
        new_topics + repeated_weakness,
        {("FUNCIONAL", "Competencia", "Debilidad"): skill("Debilidad", 5, 7)},
        performances,
        set(),
        daily_goal=5,
        now=now,
        max_official_cases=0,
    )

    diagnostic = [item for item in plan if "diagnóstico de cobertura" in item.reasons]
    assert len(diagnostic) == 2
    assert {item.question.topic for item in diagnostic} == {"A", "B"}
    assert count_topics_requiring_diagnosis(new_topics + repeated_weakness, performances) == 3


def test_study_stage_uses_coverage_then_exam_urgency():
    questions = [question("a", "A"), question("b", "B"), question("c", "C")]

    assert build_study_plan_stage(questions, {}, days_remaining=150).code == "diagnostic"
    assert build_study_plan_stage(questions, {}, days_remaining=30).code == "exam_integration"

    established = {
        item.question_id: performance(3, 0, datetime(2026, 8, 2, 12, 0))
        for item in questions
    }
    assert build_study_plan_stage(questions, established, days_remaining=150).code == "adaptive"


def test_diagnostic_stage_uses_three_of_five_questions_for_breadth():
    questions = [question(f"new-{topic}", topic) for topic in ("A", "B", "C", "D")]
    questions.extend(question(f"weak-{index}", "Debilidad") for index in range(5))
    performances = {
        f"weak-{index}": performance(0, 4, datetime(2026, 8, 1, 12, 0))
        for index in range(5)
    }
    stage = build_study_plan_stage(questions, performances, days_remaining=150)
    plan = build_hybrid_remaining_daily_plan(
        questions,
        {("FUNCIONAL", "Competencia", "Debilidad"): skill("Debilidad", 5, 7)},
        performances,
        set(),
        daily_goal=5,
        diagnostic_share=stage.diagnostic_share,
        max_official_cases=0,
    )

    diagnostic = [item for item in plan if "diagnóstico de cobertura" in item.reasons]
    assert len(diagnostic) == 3
    assert len({item.question.topic for item in diagnostic}) == 3
