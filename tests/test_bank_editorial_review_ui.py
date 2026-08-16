from pathlib import Path


PAGE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "pages" / "5_Banco_Preguntas.py"
)


def _source() -> str:
    return PAGE_PATH.read_text(encoding="utf-8-sig")


def test_candidate_approval_uses_central_quality_transition():
    source = _source()

    assert "candidate_validation_error(question)" in source
    assert "approve_candidate(question, reviewer)" in source
    assert "reject_candidate(question, reviewer, reason)" in source
    assert "record_editorial_verification(" in source


def test_editorial_form_collects_precise_source_and_distractor_analysis():
    source = _source()

    for label in (
        "URL oficial exacta",
        "Artículo, numeral o página",
        "Fragmento breve que sustenta la clave",
        "Nivel cognitivo",
        "Función de la OPEC",
        "Dificultad editorial interna",
        "Por qué cada distractor no es la mejor respuesta",
    ):
        assert label in source


def test_manual_and_import_flows_create_candidates_not_active_questions():
    source = _source()

    assert source.count('"status": "PENDING_HUMAN_REVIEW"') >= 2
    assert source.count("is_verified=False") >= 2
    assert "threshold=92" in source
