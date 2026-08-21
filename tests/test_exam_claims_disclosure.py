from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_app_does_not_present_itself_as_an_official_simulator():
    app_source = (PROJECT_ROOT / "app" / "app.py").read_text(encoding="utf-8")
    ui_source = (PROJECT_ROOT / "app" / "ui_utils.py").read_text(encoding="utf-8")

    assert "Simulador Oficial" not in app_source
    assert "DIAN Sim · Preparación para concursos" in app_source
    assert "Práctica PJS cronometrada" in ui_source


def test_results_disclose_internal_practice_index():
    results_source = (
        PROJECT_ROOT / "app" / "pages" / "3_Resultados.py"
    ).read_text(encoding="utf-8")

    assert "Según el protocolo de la CNSC" not in results_source
    assert "Puntaje Ponderado" not in results_source
    assert "Índice de práctica" in results_source
    assert "no constituye un resultado oficial" in results_source


def test_gamification_does_not_claim_unconfirmed_goa_weights():
    source = (PROJECT_ROOT / "core" / "gamification.py").read_text(encoding="utf-8")

    assert "Ponderación GOA" not in source
    assert "pesos GOA" not in source
    assert "provisional_editable_not_official_exam_weighting" in source


def test_visible_practice_labels_do_not_claim_real_or_fixed_exam_parameters():
    ui_source = (PROJECT_ROOT / "app" / "ui_utils.py").read_text(encoding="utf-8")
    config_source = (
        PROJECT_ROOT / "app" / "pages" / "7_Configuracion_OPEC.py"
    ).read_text(encoding="utf-8")
    execution_source = (
        PROJECT_ROOT / "app" / "pages" / "2_Ejecucion.py"
    ).read_text(encoding="utf-8")

    assert "Simulacros Reales" not in ui_source
    assert "100 Qs" not in ui_source
    assert "Práctica PJS cronometrada" in ui_source
    assert "cantidad y la duración oficiales siguen pendientes" in ui_source

    assert "Casos tipo examen:" not in config_source
    assert "Duración tipo examen:" not in config_source
    assert "Simulacro tipo examen" not in config_source
    assert "Casos PJS revisados:" in config_source
    assert "Duración de práctica provisional:" in config_source
    assert "meta editorial del banco local" in config_source

    assert "Caso tipo examen" not in execution_source
    assert "Caso PJS de práctica" in execution_source


def test_visible_tracks_and_thresholds_are_disclosed_as_internal_practice_rules():
    dashboard_source = (
        PROJECT_ROOT / "app" / "pages" / "6_Dashboard.py"
    ).read_text(encoding="utf-8")
    practice_source = (
        PROJECT_ROOT / "app" / "pages" / "1_Nuevo_Simulacro.py"
    ).read_text(encoding="utf-8")
    bank_source = (
        PROJECT_ROOT / "app" / "pages" / "5_Banco_Preguntas.py"
    ).read_text(encoding="utf-8")

    assert "Nivel de Dominio por Eje" not in dashboard_source
    assert "Meta 70%" not in dashboard_source
    assert "área de práctica" in dashboard_source
    assert "Meta interna 70%" not in dashboard_source
    assert "Umbral interno de refuerzo: 70%" in dashboard_source

    assert 'st.multiselect("Eje"' not in practice_source
    assert "Progresión interna 1–10" in practice_source
    assert "no una escala de la CNSC" in practice_source
    assert "cantidad, duración y ponderación oficiales siguen pendientes" in practice_source

    assert 'st.selectbox("Eje"' not in bank_source
    assert '"Track / Eje"' not in bank_source
    assert "no equivale a ejes oficiales del examen" in bank_source


def test_core_messages_and_ai_prompts_do_not_impersonate_exam_authorities():
    readiness_source = (
        PROJECT_ROOT / "core" / "competition_readiness.py"
    ).read_text(encoding="utf-8")
    adaptive_source = (PROJECT_ROOT / "core" / "adaptive.py").read_text(
        encoding="utf-8"
    )
    llm_source = (
        PROJECT_ROOT / "core" / "generators" / "llm.py"
    ).read_text(encoding="utf-8")

    assert "casos tipo examen" not in readiness_source
    assert "simulacro tipo examen" not in readiness_source
    assert "sesión provisional de 30 preguntas" in readiness_source
    assert "casos PJS de práctica" in readiness_source

    assert "caso tipo examen" not in adaptive_source
    assert "formato GOA se practica" not in adaptive_source
    assert "metodología PJS se practica" in adaptive_source

    assert "Constructor de Pruebas Psicométricas Senior de la CNSC" not in llm_source
    assert "Tutor Experto de la DIAN" not in llm_source
    assert "Diseñador de Pruebas Situacionales para la DIAN" not in llm_source
    assert "No afirmes representar a la CNSC ni a la DIAN" in llm_source
    assert "su oficialidad y vigencia deben verificarse" in llm_source
