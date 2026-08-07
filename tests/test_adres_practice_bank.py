from collections import Counter

from core.question_banks.adres_practice import build_adres_practice_questions


def test_adres_practice_bank_has_70_varied_classified_questions():
    questions = build_adres_practice_questions()
    assert len(questions) == 70
    assert len({question["stem"] for question in questions}) == 70
    assert Counter(question["track"] for question in questions) == {"FUNCIONAL": 48, "COMPORTAMENTAL": 22}
    assert {question["function_number"] for question in questions if question["track"] == "FUNCIONAL"} == set(range(1, 17))
    assert all(tuple(question["options"]) == ("A", "B", "C") for question in questions)
    assert all(question["correct_key"] in question["options"] for question in questions)


def test_every_adres_function_has_basic_intermediate_and_advanced_questions():
    questions = build_adres_practice_questions()
    for function_number in range(1, 17):
        levels = {q["difficulty"] for q in questions if q["function_number"] == function_number}
        assert levels == {1, 2, 3}


def test_adres_bank_is_marked_provisional_until_official_guide_arrives():
    questions = build_adres_practice_questions()
    assert all("guía oficial pendiente" in question["source_refs"] for question in questions)
