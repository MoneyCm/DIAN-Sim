from core.question_banks.dian_analista_i_242699 import CASE_SPECS, case_questions, standalone_questions


def test_initial_bank_has_complete_function_coverage():
    assert len(CASE_SPECS) == 10
    assert {item[0] for item in CASE_SPECS} == set(range(1, 11))
    assert sum(len(case_questions(item, index)) for index, item in enumerate(CASE_SPECS, start=1)) == 30
    assert sum(len(standalone_questions(item, index)) for index, item in enumerate(CASE_SPECS, start=1)) == 70


def test_every_question_has_three_choices_and_one_key():
    for index, spec in enumerate(CASE_SPECS, start=1):
        for row in [*case_questions(spec, index), *standalone_questions(spec, index)]:
            assert set(row["options"]) == {"A", "B", "C"}
            assert row["correct_key"] in row["options"]
            assert row["rationale"]
