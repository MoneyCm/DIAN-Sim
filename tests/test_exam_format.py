from types import SimpleNamespace

from core.exam_format import (
    LIKERT_OPTIONS, OFFICIAL_LABEL, PRACTICE_LABEL, REVIEW_LABEL,
    build_official_case_blocks, build_trusted_pjs_case_blocks,
    is_official_functional_case, is_official_functional_payload,
    is_trusted_pjs_case, question_format_status, trusted_pjs_question_groups,
)


def question(track="FUNCIONAL", options=None, correct_key="A", question_type="SITUATIONAL", is_verified=True, trusted=True):
    return SimpleNamespace(
        track=track,
        options_json=options or {"A": "Uno", "B": "Dos", "C": "Tres"},
        correct_key=correct_key,
        question_type=question_type,
        stem="Enunciado",
        is_verified=is_verified,
        quality_report={"status": "APPROVED", "review": "human_source_grounded"} if trusted else None,
    )


def precise_question(question_id="q-1"):
    item = question()
    item.question_id = question_id
    item.quality_report["source_verification"] = {
        "status": "official_current",
        "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
        "locator": "Artículo 684",
        "supporting_excerpt": "La Administración Tributaria tiene amplias facultades de fiscalización.",
        "verified_on": "2026-08-15",
        "verified_by": "revisión editorial de prueba",
    }
    return item


def test_official_case_requires_three_functional_statements():
    case = SimpleNamespace(text="Caso laboral", questions=[question(), question(), question()])
    assert is_official_functional_case(case)
    case.questions.pop()
    assert not is_official_functional_case(case)


def test_official_case_rejects_wrong_track_or_options():
    case = SimpleNamespace(text="Caso", questions=[question(), question(), question(track="INTEGRIDAD")])
    assert not is_official_functional_case(case)


def test_legacy_verified_question_without_grounded_review_is_not_official():
    legacy = question(trusted=False)
    case = SimpleNamespace(text="Caso", questions=[legacy, question(), question()])
    legacy.case_study = case
    assert not is_official_functional_case(case)
    assert question_format_status(legacy) == REVIEW_LABEL
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

def test_verified_ten_question_case_yields_three_non_destructive_blocks():
    questions = [question() for _ in range(10)]
    for index, item in enumerate(questions):
        item.question_id = str(index)
        item.created_at = str(index).zfill(2)
    case = SimpleNamespace(
        id="case-1", title="Caso", text="Contexto", topic="Tema",
        difficulty=3, competition_id=1, questions=questions,
    )
    blocks = build_official_case_blocks([case])
    assert len(blocks) == 3
    assert all(len(block.questions) == 3 for block in blocks)
    assert len(case.questions) == 10


def test_measurement_pjs_requires_precise_official_source_proof():
    legacy = question()
    legacy.question_id = "legacy"
    case = SimpleNamespace(
        id="case-precise",
        title="Caso",
        text="Contexto laboral",
        topic="Fiscalización",
        difficulty=3,
        competition_id=1,
        questions=[legacy],
    )

    assert trusted_pjs_question_groups(case) == []
    assert build_trusted_pjs_case_blocks([case], eligible_question_ids={"legacy"}) == []


def test_measurement_pjs_accepts_one_to_three_items_and_keeps_remainder():
    questions = [precise_question(f"q-{index}") for index in range(4)]
    for index, item in enumerate(questions):
        item.created_at = index
    case = SimpleNamespace(
        id="case-pjs",
        title="Caso",
        text="Contexto laboral aplicable al empleo",
        topic="Fiscalización",
        difficulty=3,
        competition_id=1,
        questions=questions,
    )

    blocks = build_trusted_pjs_case_blocks(
        [case],
        eligible_question_ids={item.question_id for item in questions},
        opec_number="236769",
    )

    assert [len(block.questions) for block in blocks] == [3, 1]
    assert all(is_trusted_pjs_case(block) for block in blocks)
    assert all(block.opec_number == "236769" for block in blocks)
    assert all(block.bank_partition == "measurement" for block in blocks)
