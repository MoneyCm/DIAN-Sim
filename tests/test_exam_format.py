from types import SimpleNamespace

from core.exam_format import (
    LIKERT_OPTIONS, OFFICIAL_LABEL, PRACTICE_LABEL, REVIEW_LABEL,
    is_official_functional_case, is_official_functional_payload, question_format_status,
)


def question(track="FUNCIONAL", options=None, correct_key="A", question_type="SITUATIONAL"):
    return SimpleNamespace(
        track=track,
        options_json=options or {"A": "Uno", "B": "Dos", "C": "Tres"},
        correct_key=correct_key,
        question_type=question_type,
        stem="Enunciado",
    )


def test_official_case_requires_three_functional_statements():
    case = SimpleNamespace(text="Caso laboral", questions=[question(), question(), question()])
    assert is_official_functional_case(case)
    case.questions.pop()
    assert not is_official_functional_case(case)


def test_official_case_rejects_wrong_track_or_options():
    case = SimpleNamespace(text="Caso", questions=[question(), question(), question(track="INTEGRIDAD")])
    assert not is_official_functional_case(case)
    case.questions[2] = question(options={"A": "Uno", "B": "Dos", "C": "Tres", "D": "Cuatro"})
    assert not is_official_functional_case(case)


def test_likert_scale_has_four_choices_and_no_neutral():
    assert len(LIKERT_OPTIONS) == 4
    assert all("Neutral" not in option for option in LIKERT_OPTIONS)


def test_generated_payload_must_match_official_case_shape():
    payload = {
        "text": "Caso laboral",
        "questions": [
            {"track": "FUNCIONAL", "stem": str(i), "options": {"A": "1", "B": "2", "C": "3"}, "correct_key": "A"}
            for i in range(3)
        ],
    }
    assert is_official_functional_payload(payload)
    payload["questions"][0]["track"] = "COMPORTAMENTAL"
    assert not is_official_functional_payload(payload)

def test_question_format_status_is_non_destructive():
    official_case = SimpleNamespace(text="Caso", questions=[question(), question(), question()])
    official_question = official_case.questions[0]
    official_question.case_study = official_case
    assert question_format_status(official_question) == OFFICIAL_LABEL

    review_case = SimpleNamespace(text="Caso", questions=[question()])
    review_case.questions[0].case_study = review_case
    assert question_format_status(review_case.questions[0]) == REVIEW_LABEL

    assert question_format_status(question()) == PRACTICE_LABEL