from core.generated_questions import candidate_issues, extract_candidates


def test_generation_candidate_uses_canonical_difficulty_scale():
    row = extract_candidates({"questions": [{
        "stem": "La dependencia documenta un hallazgo y debe decidir cómo continuar.",
        "options": {"A": "Aplicar la regla", "B": "Omitirla", "C": "Delegar sin revisar"},
        "correct_key": "A",
        "rationale": "La opción A mantiene el control y la trazabilidad.",
        "source_refs": "Manual de funciones, función 6",
        "difficulty": 9,
    }]})[0]

    assert row["difficulty"] == 9


def test_import_normalizes_options_and_source():
    rows = extract_candidates({"questions": [{
        "stem": "Caso", "options": {"A": "Uno", "B": "Dos", "C": "Tres"},
        "correct_key": "b", "rationale": "Norma aplicable",
    }]}, source_ref="ET art. 684")
    assert rows[0]["correct_key"] == "B"
    assert rows[0]["source_refs"] == "ET art. 684"
    assert candidate_issues(rows[0]) == []


def test_candidate_rejects_four_options_and_missing_source():
    row = extract_candidates([{
        "stem": "Caso", "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "correct_key": "A", "rationale": "Porque sí",
    }])[0]
    assert len(candidate_issues(row)) == 2


def test_candidate_flags_content_that_drifted_from_source():
    row = extract_candidates([{
        "stem": "Caso sobre factura electrónica", "options": {"A": "1", "B": "2", "C": "3"},
        "correct_key": "A", "rationale": "Transmisión de la factura", "source_refs": "ET 684",
    }])[0]
    issues = candidate_issues(
        row, "Facultades de fiscalización e investigación del artículo 684"
    )
    assert "No se observa suficiente sustento en el texto proporcionado" in issues


def test_candidate_flags_topic_that_adds_an_unrelated_procedure():
    row = extract_candidates([{
        "topic": "Análisis preliminar de denuncias para iniciar fiscalización",
        "stem": "La autoridad ejerce facultades de fiscalización e investigación",
        "options": {"A": "1", "B": "2", "C": "3"}, "correct_key": "A",
        "rationale": "Aplica el artículo 684", "source_refs": "ET 684",
    }])[0]
    issues = candidate_issues(
        row, "El artículo 684 establece facultades de fiscalización e investigación"
    )
    assert "No se observa suficiente sustento en el texto proporcionado" in issues


def test_candidate_accepts_one_semantic_match_with_same_article():
    row = extract_candidates([{
        "topic": "Candidato generado",
        "stem": "La autoridad revisa la actuación",
        "options": {"A": "1", "B": "2", "C": "3"},
        "correct_key": "A",
        "rationale": "Aplica la fiscalización",
        "source_refs": "ET, artículo 684",
    }])[0]

    issues = candidate_issues(
        row,
        "El artículo 684 regula las facultades de fiscalización",
    )

    assert "No se observa suficiente sustento en el texto proporcionado" not in issues


def test_candidate_does_not_match_references_only_by_year():
    row = extract_candidates([{
        "topic": "Candidato generado",
        "stem": "La autoridad realiza una fiscalización",
        "options": {"A": "1", "B": "2", "C": "3"},
        "correct_key": "A",
        "rationale": "Debe aplicar la regla correspondiente",
        "source_refs": "Ley 999 de 2019, artículo 99",
    }])[0]

    issues = candidate_issues(
        row,
        "El Decreto 1165 de 2019 regula la fiscalización aduanera",
    )

    assert "No se observa suficiente sustento en el texto proporcionado" in issues
