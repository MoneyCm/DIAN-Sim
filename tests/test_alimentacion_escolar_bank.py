from core.question_banks.alimentacion_escolar import (
    ADVANCED_CASE_COUNT,
    ADVANCED_QUESTION_COUNT,
    TARGET_COUNT,
    build_advanced_case_questions,
    build_questions,
)


def test_bank_has_target_count_and_unique_stems():
    questions = build_questions()
    assert len(questions) == TARGET_COUNT == 100
    assert len({question["stem"] for question in questions}) == TARGET_COUNT


def test_all_questions_are_complete_and_answers_rotate():
    questions = build_questions()
    keys = {question["correct"] for question in questions}
    assert keys == {"A", "B", "C"}
    for question in questions:
        assert set(question["options"]) == {"A", "B", "C"}
        assert question["correct"] in question["options"]
        assert question["rationale"]
        assert question["source"]


def test_advanced_cases_have_exam_structure():
    cases = build_advanced_case_questions()
    assert len(cases) == ADVANCED_CASE_COUNT == 10
    assert sum(len(case["questions"]) for case in cases) == ADVANCED_QUESTION_COUNT == 30
    assert all(len(case["text"]) >= 250 for case in cases)
    assert all(len(case["questions"]) == 3 for case in cases)
    assert {question["correct"] for case in cases for question in case["questions"]} == {"A", "B", "C"}
