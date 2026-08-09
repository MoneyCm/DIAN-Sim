from types import SimpleNamespace

from core.question_quality import audit_bank, audit_question_structure, store_deterministic_audit


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
