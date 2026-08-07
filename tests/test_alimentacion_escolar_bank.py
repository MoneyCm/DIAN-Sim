from core.question_banks.alimentacion_escolar import TARGET_COUNT, build_questions


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
