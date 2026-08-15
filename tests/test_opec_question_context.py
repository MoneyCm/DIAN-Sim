from types import SimpleNamespace

from core.opec_question_context import (
    function_number_for_question,
    manual_function_context,
    matches_manual_function_filter,
)


def question(**values):
    base = {"case_id": None, "case_study": None, "topic": "", "source_refs": "", "micro_competencia": ""}
    base.update(values)
    return SimpleNamespace(**base)


def test_known_opec_case_maps_to_its_explicit_manual_function():
    item = question(case_id="goa-236769-denuncias-precritica-01")

    assert function_number_for_question(item, "236769") == 2


def test_source_function_marker_maps_and_displays_the_manual_text():
    item = question(source_refs="OPEC 123 · Función 2: control de expedientes")
    context = manual_function_context(item, "123", ["Primera función", "Segunda función"])

    assert context == {"number": 2, "text": "Segunda función"}


def test_function_filter_uses_only_explicit_mappings():
    item = question(topic="OPEC 236769 F05 · Fiscalización")

    assert matches_manual_function_filter(item, "236769", [5])
    assert not matches_manual_function_filter(item, "236769", [2])
