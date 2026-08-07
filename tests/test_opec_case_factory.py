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
    assert "ADRES" in payload["text"]
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


def test_adres_case_catalog_is_varied_and_contains_no_dian_context():
    opec = SimpleNamespace(
        job_title="GESTOR DE OPERACIONES Grado 9",
        purpose="Gestionar proyectos de TI.",
        functions=[f"Función técnica {index}." for index in range(1, 17)],
    )

    cases = [build_fallback_opec_case(opec, number) for number in range(1, 11)]

    assert len({case["title"] for case in cases}) == 10
    assert all("ADRES" in case["text"] for case in cases)
    assert all("DIAN" not in case["text"] for case in cases)
    assert all(is_official_functional_payload(case) for case in cases)
    assert all("¿Cuál es la actuación" in case["questions"][0]["stem"] for case in cases)
    assert "Función técnica 13" in cases[5]["text"]
    assert "Función técnica 6" in cases[6]["text"]
