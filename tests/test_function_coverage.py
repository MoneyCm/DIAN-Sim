from types import SimpleNamespace

from core.function_coverage import build_function_coverage


def question(qid, text, trusted=True):
    return SimpleNamespace(
        question_id=qid, macro_dominio="Tributario", micro_competencia=None,
        competency="Fiscalización", topic=text, stem=text, rationale=text,
        source_refs="Estatuto Tributario", is_verified=trusted,
        quality_report={"review": "human_source_grounded"} if trusted else None,
    )


def test_function_mapping_does_not_force_unrelated_questions():
    functions = ["Analizar denuncias de fiscalización y establecer su pertinencia"]
    rows, unmatched = build_function_coverage(functions, [question("1", "Trabajo en equipo")], [])
    assert rows[0]["questions"] == 0
    assert unmatched == 1


def test_function_mapping_assigns_clear_matches_to_one_function():
    functions = [
        "Analizar denuncias de fiscalización y establecer su pertinencia",
        "Practicar pruebas solicitadas dentro de una investigación tributaria",
    ]
    rows, unmatched = build_function_coverage(
        functions, [question("1", "práctica de pruebas en investigación tributaria")], []
    )
    assert rows[0]["questions"] == 0
    assert rows[1]["questions"] == 1
    assert unmatched == 0

