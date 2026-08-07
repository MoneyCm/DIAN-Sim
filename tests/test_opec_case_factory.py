from types import SimpleNamespace

from core.exam_format import is_official_functional_payload
from core.opec_case_factory import build_fallback_opec_case, build_fallback_questions


def test_fallback_opec_case_has_official_triplet_format():
    opec = SimpleNamespace(
        opec_number="252097",
        job_title="GESTOR DE OPERACIONES Grado 9",
        purpose="Gestionar proyectos y requerimientos de TI.",
        functions=["Gestionar seguridad y privacidad de la información."],
    )

    payload = build_fallback_opec_case(opec, 3)

    assert is_official_functional_payload(payload)
    assert "seguridad y privacidad" in payload["text"]
    assert len(payload["questions"]) == 3


def test_fallback_questions_are_unique_and_have_valid_options():
    opec = SimpleNamespace(
        job_title="GESTOR DE OPERACIONES Grado 9",
        purpose="Gestionar proyectos de TI.",
        functions=["Gestionar seguridad.", "Administrar bases de datos."],
    )

    questions = build_fallback_questions(opec, "FUNCIONAL", 12)

    assert len(questions) == 12
    assert len({question["stem"] for question in questions}) == 12
    assert all(tuple(question["options"]) == ("A", "B", "C") for question in questions)
    assert all(question["correct_key"] in question["options"] for question in questions)


def test_fallback_questions_cover_behavioral_and_integrity():
    opec = SimpleNamespace(job_title="Gestor", purpose="Gestionar", functions=[])

    behavioral = build_fallback_questions(opec, "COMPORTAMENTAL", 2)
    integrity = build_fallback_questions(opec, "INTEGRIDAD", 2)

    assert all(question["correct_key"] == "A" for question in behavioral)
    assert all(question["correct_key"] == "C" for question in integrity)
