from types import SimpleNamespace

from core.preparation_matrix import build_master_preparation_matrix, load_preparation_blueprint


FUNCTIONS = [f"Función oficial {number}" for number in range(1, 10)]


def question(number, *, verified=True, reviewed=True, question_id=None):
    case = SimpleNamespace(id=f"case-{number}")
    return SimpleNamespace(
        question_id=question_id or f"q-{number}",
        case_id=case.id,
        case_study=case,
        topic=f"OPEC 236769 F{number:02d} · Tema",
        micro_competencia=f"OPEC 236769 F{number:02d} · Tema",
        is_verified=verified,
        quality_report={
            "review": "human_source_grounded",
            "source_verification": {
                "status": "official_current",
                "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
                "locator": "Artículo 1",
                "supporting_excerpt": "Fragmento oficial suficiente para respaldar la respuesta correcta.",
                "verified_on": "2026-08-15",
                "verified_by": "editorial-test",
            },
        } if reviewed else {},
    )


def test_blueprint_has_nine_functions_and_requested_bank_target():
    blueprint = load_preparation_blueprint("236769")
    assert len(blueprint["functions"]) == 9
    assert [item["number"] for item in blueprint["functions"]] == list(range(1, 10))
    assert blueprint["functions"][0]["short_name"] == "Precrítica y clasificación de insumos"
    assert blueprint["functions"][4]["short_name"].startswith("Revisión técnica")
    assert blueprint["functions"][8]["short_name"].startswith("Funciones comunes")
    assert sum(item["functional_question_target"] for item in blueprint["functions"]) == 1500
    assert blueprint["bank_targets"] == {
        "functional": 1500,
        "behavioral": 400,
        "integrity": 300,
    }
    assert blueprint["official_exam_methodology"]["functional"]["method"].startswith(
        "Prueba de Juicio Situacional"
    )
    assert blueprint["official_exam_methodology"]["behavioral"]["has_correct_answer"] is False


def test_matrix_combines_coverage_sources_and_user_evidence():
    questions = [question(number) for number in range(1, 10)]
    performances = [SimpleNamespace(
        question_id="q-1", hits=4, misses=1, mastery_level=8.0
    )]

    matrix = build_master_preparation_matrix("236769", FUNCTIONS, questions, performances)

    assert matrix["available"] is True
    assert matrix["trusted_question_count"] == 9
    assert matrix["unmatched_questions"] == 0
    assert len(matrix["rows"]) == 9
    first = matrix["rows"][0]
    assert first["question_count"] == 1
    assert first["trusted_question_count"] == 1
    assert first["case_count"] == 1
    assert first["attempt_count"] == 5
    assert first["accuracy"] == 0.8
    assert first["mastery"] == 0.8
    assert first["sources"]


def test_matrix_normalizes_canonical_mastery_level_from_zero_to_ten():
    matrix = build_master_preparation_matrix(
        "236769",
        FUNCTIONS,
        [question(1)],
        [SimpleNamespace(question_id="q-1", hits=6, misses=4, mastery_level=5.5)],
    )

    assert matrix["rows"][0]["mastery"] == 0.55


def test_fractional_mastery_is_not_reinterpreted_as_a_zero_to_one_scale():
    matrix = build_master_preparation_matrix(
        "236769",
        FUNCTIONS,
        [question(1)],
        [SimpleNamespace(question_id="q-1", hits=1, misses=1, mastery_level=0.8)],
    )

    assert matrix["rows"][0]["mastery"] == 0.08


def test_matrix_clamps_mastery_to_canonical_limits():
    low = build_master_preparation_matrix(
        "236769",
        FUNCTIONS,
        [question(1)],
        [SimpleNamespace(question_id="q-1", hits=1, misses=1, mastery_level=-2.0)],
    )
    high = build_master_preparation_matrix(
        "236769",
        FUNCTIONS,
        [question(1)],
        [SimpleNamespace(question_id="q-1", hits=1, misses=1, mastery_level=12.0)],
    )

    assert low["rows"][0]["mastery"] == 0.0
    assert high["rows"][0]["mastery"] == 1.0


def test_matrix_does_not_report_mastery_without_attempt_evidence():
    matrix = build_master_preparation_matrix(
        "236769",
        FUNCTIONS,
        [question(1)],
        [SimpleNamespace(question_id="q-1", hits=0, misses=0, mastery_level=8.0)],
    )

    first = matrix["rows"][0]
    assert first["attempt_count"] == 0
    assert first["exposed_question_count"] == 0
    assert first["mastery"] == 0.0


def test_matrix_never_counts_unreviewed_question_as_trusted():
    matrix = build_master_preparation_matrix(
        "236769", FUNCTIONS, [question(1, verified=True, reviewed=False)], []
    )
    assert matrix["rows"][0]["question_count"] == 1
    assert matrix["rows"][0]["trusted_question_count"] == 0


def test_unknown_opec_has_no_invented_blueprint():
    matrix = build_master_preparation_matrix("999999", [], [], [])
    assert matrix == {"available": False, "rows": [], "unmatched_questions": 0}
