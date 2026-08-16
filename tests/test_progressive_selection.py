from types import SimpleNamespace

from core.adaptive import select_questions_for_simulation


def question(question_id, difficulty):
    return SimpleNamespace(
        question_id=question_id, case_study=None, track="FUNCIONAL",
        competency="Arquitectura", topic="F13 · Arquitectura", difficulty=difficulty,
    )


def test_personalized_practice_starts_with_basic_questions():
    questions = [question(f"q{difficulty}-{index}", difficulty) for difficulty in (1, 2, 3) for index in range(4)]
    selected = select_questions_for_simulation(questions, {}, n=4)
    assert {item.difficulty for item in selected} == {1}


def test_personalized_practice_does_not_unlock_advanced_from_mastery_alone():
    questions = [question(f"q{difficulty}-{index}", difficulty) for difficulty in (1, 2, 3) for index in range(4)]
    skill = SimpleNamespace(mastery_score=82)
    selected = select_questions_for_simulation(
        questions, {("FUNCIONAL", "Arquitectura", "F13 · Arquitectura"): skill}, n=4
    )
    # A legacy Skill has no evidence of new questions, delayed retention or
    # measurement; its score alone cannot unlock harder content.
    assert {item.difficulty for item in selected} == {1}


def test_personalized_practice_uses_a_complete_goa_case_before_mastery(monkeypatch):
    case = SimpleNamespace(id="goa-case", questions=[])
    questions = [
        SimpleNamespace(
            question_id=f"goa-{index}", case_study=case, track="FUNCIONAL",
            competency="Fiscalización", topic="F01", difficulty=1,
        )
        for index in range(3)
    ]
    case.questions = questions

    monkeypatch.setattr("core.exam_format.official_question_groups", lambda _: [questions])

    selected = select_questions_for_simulation(questions, {}, n=3)

    assert [item.question_id for item in selected] == ["goa-0", "goa-1", "goa-2"]
