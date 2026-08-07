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


def test_personalized_practice_unlocks_advanced_questions_after_mastery():
    questions = [question(f"q{difficulty}-{index}", difficulty) for difficulty in (1, 2, 3) for index in range(4)]
    skill = SimpleNamespace(mastery_score=82)
    selected = select_questions_for_simulation(
        questions, {("FUNCIONAL", "Arquitectura", "F13 · Arquitectura"): skill}, n=4
    )
    assert {item.difficulty for item in selected} == {3}
