from collections import Counter
from types import SimpleNamespace

from core.question_banks.opec_progressive import (
    BANK_VERSION,
    build_opec_progressive_questions,
    classify_function,
)


def _opec(functions):
    return SimpleNamespace(opec_number="241130", job_title="Profesional Especializado", purpose="Apoyar la gestión estratégica", functions=functions)


def test_generic_bank_covers_every_function_at_three_levels():
    functions = [
        "Coordinar grupos de trabajo permanentes",
        "Elaborar planes de acción e inversiones",
        "Revisar metas con indicadores de impacto",
        "Gestionar la aprobación del presupuesto",
    ]
    questions = build_opec_progressive_questions(_opec(functions), "TERRITORIAL-12-BOLIVAR")
    assert len(questions) == 70
    assert Counter(q["track"] for q in questions) == {"FUNCIONAL": 48, "COMPORTAMENTAL": 22}
    for number in range(1, len(functions) + 1):
        assert {q["difficulty"] for q in questions if q["function_number"] == number} == {1, 2, 3}
    assert all(BANK_VERSION in q["source_refs"] for q in questions)


def test_classifier_is_not_limited_to_ti_or_adres():
    assert classify_function("Semaforizar el cumplimiento de metas e indicadores")[0] == "Seguimiento y evaluación"
    assert classify_function("Gestionar el modelo de seguridad y privacidad")[0] == "Seguridad y privacidad"


def test_generic_bank_uses_the_supplied_opec_and_not_adres_text():
    questions = build_opec_progressive_questions(_opec(["Coordinar el equipo"]), "OTRO")
    text = " ".join(q["stem"] + " " + q["source_refs"] for q in questions)
    assert "241130" in text
    assert "252097" not in text
