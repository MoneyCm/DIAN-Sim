from types import SimpleNamespace

from core.question_quality import (
    audit_bank,
    audit_question_structure,
    find_near_duplicate_pairs,
    store_deterministic_audit,
)


def question(**overrides):
    values = dict(
        question_id="q1", stem="Una entidad debe decidir cómo actuar ante un riesgo documentado. ¿Qué debe hacer?",
        options_json={"A": "Documentar y aplicar el procedimiento.", "B": "Ignorar el riesgo.", "C": "Actuar sin competencia."},
        correct_key="A", rationale="La actuación conserva trazabilidad y aplica el procedimiento establecido.",
        source_refs="Manual de funciones, función 3", difficulty=2,
        competency="Gestión", topic="Función 3", quality_report=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_valid_structure_passes_without_becoming_verified():
    item = question()
    report = audit_question_structure(item)
    assert report["status"] == "PASS"
    store_deterministic_audit(item, report)
    assert item.quality_report["deterministic_audit"]["score"] == 100
    assert not hasattr(item, "is_verified")


def test_missing_source_and_duplicate_options_require_review():
    item = question(source_refs="", options_json={"A": "Igual", "B": "Igual", "C": "Otra"})
    report = audit_question_structure(item)
    assert report["status"] == "REVIEW"
    assert {finding["code"] for finding in report["findings"]} >= {"missing_source", "duplicate_options"}


def test_bank_reports_answer_key_bias():
    items = [question(question_id=f"q{i}", correct_key="A") for i in range(4)]
    summary = audit_bank(items)
    assert summary["passed"] == 4
    assert summary["dominant_key"] == "A"
    assert summary["dominant_key_pct"] == 100.0


def test_likert_structure_requires_four_options_and_no_key():
    item = question(
        track="COMPORTAMENTAL",
        question_type="LIKERT",
        options_json={"A": "Nunca", "B": "Casi nunca", "C": "Casi siempre", "D": "Siempre"},
        correct_key=None,
    )
    assert audit_question_structure(item)["status"] == "PASS"

    item.correct_key = "A"
    report = audit_question_structure(item)
    assert report["status"] == "REVIEW"
    assert "likert_has_key" in {finding["code"] for finding in report["findings"]}


def test_concise_likert_statement_is_valid_without_forcing_a_case_prompt():
    item = question(
        stem="Actúo coordinadamente con mi equipo.",
        track="COMPORTAMENTAL",
        question_type="LIKERT",
        options_json={"A": "Nunca", "B": "Casi nunca", "C": "Casi siempre", "D": "Siempre"},
        correct_key=None,
    )

    assert audit_question_structure(item)["status"] == "PASS"


def test_likert_items_do_not_distort_answer_key_bias():
    functional = question(question_id="functional", correct_key="B")
    likert = question(
        question_id="likert",
        track="INTEGRIDAD",
        question_type="LIKERT",
        options_json={"A": "1", "B": "2", "C": "3", "D": "4"},
        correct_key=None,
    )
    summary = audit_bank([functional, likert])
    assert summary["dominant_key"] == "B"
    assert summary["dominant_key_pct"] == 50.0


def test_editorial_difficulty_accepts_full_one_to_ten_scale():
    item = question(quality_report={"editorial_difficulty_1_10": 9})
    assert audit_question_structure(item)["status"] == "PASS"


def test_near_duplicate_paraphrases_are_reported_for_editorial_review():
    first = question(
        question_id="first",
        stem="La dependencia recibe un hallazgo documentado y debe definir la actuación inicial.",
    )
    second = question(
        question_id="second",
        stem="La dependencia debe definir la actuación inicial ante un hallazgo documentado.",
    )

    pairs = find_near_duplicate_pairs([first, second], threshold=85)
    summary = audit_bank([first, second])

    assert pairs[0]["question_id"] == "first"
    assert pairs[0]["duplicate_question_id"] == "second"
    assert summary["near_duplicate_count"] == 1
