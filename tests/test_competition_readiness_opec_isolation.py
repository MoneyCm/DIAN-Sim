import ast
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.competition_readiness import inspect_competition
from db.models import (
    Base,
    CaseOpecScope,
    CaseStudy,
    Competition,
    OpecProfile,
    Question,
    QuestionOpecScope,
)


ROOT = Path(__file__).resolve().parents[1]


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _question(competition_id, case_id, opec_number, index):
    return Question(
        question_id=f"q-{opec_number}-{index}",
        competition_id=competition_id,
        case_id=case_id,
        track="FUNCIONAL",
        competency="Aplicación",
        topic=f"OPEC {opec_number} F01 · Fiscalización",
        difficulty=2,
        question_type="SITUATIONAL",
        stem=f"Situación de la OPEC {opec_number}, pregunta {index}.",
        options_json={"A": "Correcta", "B": "Distractor", "C": "Distractor"},
        correct_key="A",
        rationale="Justificación contrastada.",
        source_refs=f"OPEC {opec_number} · fuente",
        hash_norm=f"hash-{opec_number}-{index}",
        is_verified=True,
        quality_report={"review": "human_source_grounded"},
    )


def _scoped_case(db, competition, profile, opec_number):
    case = CaseStudy(
        id=f"case-{opec_number}",
        competition_id=competition.id,
        title=f"Caso OPEC {opec_number}",
        text="Una situación laboral completa y verificable.",
        topic="Fiscalización",
        difficulty=2,
    )
    db.add(case)
    questions = [
        _question(competition.id, case.id, opec_number, index)
        for index in range(1, 4)
    ]
    db.add_all(questions)
    db.flush()
    db.add(CaseOpecScope(case_id=case.id, opec_profile_id=profile.id))
    db.add_all([
        QuestionOpecScope(
            question_id=question.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        )
        for question in questions
    ])
    return questions


def test_readiness_does_not_mix_opecs_from_the_same_competition():
    db = _db()
    competition = Competition(code="DIAN-SHARED", name="DIAN compartido")
    db.add(competition)
    db.flush()
    first = OpecProfile(competition_id=competition.id, opec_number="236769")
    second = OpecProfile(competition_id=competition.id, opec_number="242699")
    db.add_all([first, second])
    db.flush()
    _scoped_case(db, competition, first, "236769")
    _scoped_case(db, competition, second, "242699")
    anchor = _question(competition.id, None, "236769", 98)
    db.add(anchor)
    db.flush()
    db.add(QuestionOpecScope(
        question_id=anchor.question_id,
        opec_profile_id=first.id,
        bank_partition="anchor",
    ))
    # It mentions the first OPEC, but canonical scope is authoritative and it
    # must remain quarantined because it has no association row.
    db.add(_question(competition.id, None, "236769", 99))
    db.commit()

    first_readiness = inspect_competition(
        db, competition.id, opec_number="236769"
    )
    second_readiness = inspect_competition(
        db, competition.id, opec_number="242699"
    )
    whole_competition = inspect_competition(db, competition.id)

    assert first_readiness.question_count == 3
    assert first_readiness.enabled_question_count == 3
    assert first_readiness.official_case_count == 1
    assert first_readiness.reviewed_practice_case_count == 1
    assert second_readiness.question_count == 3
    assert second_readiness.official_case_count == 1
    assert whole_competition.question_count == 8
    assert whole_competition.official_case_count == 2


def test_empty_canonical_scope_does_not_fall_back_to_text_matching():
    db = _db()
    competition = Competition(code="DIAN-EMPTY", name="DIAN vacío")
    db.add(competition)
    db.flush()
    db.add(OpecProfile(competition_id=competition.id, opec_number="236769"))
    db.add(_question(competition.id, None, "236769", 1))
    db.commit()

    readiness = inspect_competition(db, competition.id, opec_number="236769")

    assert readiness.question_count == 0
    assert readiness.enabled_question_count == 0
    assert readiness.official_case_count == 0


def test_legacy_bank_falls_back_to_unambiguous_opec_evidence():
    db = _db()
    competition = Competition(code="DIAN-LEGACY", name="DIAN legado")
    db.add(competition)
    db.flush()
    db.add_all([
        _question(competition.id, None, "236769", 1),
        _question(competition.id, None, "242699", 1),
    ])
    db.commit()

    readiness = inspect_competition(db, competition.id, opec_number="236769")

    assert readiness.question_count == 1
    assert readiness.enabled_question_count == 1


def test_bank_page_uses_one_opec_inventory_for_all_visible_views():
    source = (ROOT / "app" / "pages" / "5_Banco_Preguntas.py").read_text(
        encoding="utf-8"
    )

    assert "quality_questions = list(active_bank_items)" in source
    assert "queue_questions = list(active_bank_items)" in source
    assert "bank_items = list(active_bank_items)" in source
    assert "active_bank_items = retain_training_partition(" in source
    assert 'QuestionOpecScope.bank_partition == "training"' in source
    assert "Question.competition_id == competition_id" not in source
    assert "retain_allowed_questions(selected_qs, active_bank_ids)" in source
    assert 'str(q_to_del.question_id) in active_bank_ids' in source


def test_bank_bulk_guard_rejects_stale_ids_from_another_opec():
    path = ROOT / "app" / "pages" / "5_Banco_Preguntas.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "retain_allowed_questions"
    )
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)

    selected = [
        SimpleNamespace(question_id="opec-a"),
        SimpleNamespace(question_id="opec-b"),
    ]

    assert namespace["retain_allowed_questions"](selected, {"opec-a"}) == [
        selected[0]
    ]


def test_every_readiness_page_passes_the_opec_identity():
    pages = (
        ROOT / "app" / "pages" / "7_Configuracion_OPEC.py",
        ROOT / "app" / "pages" / "14_Mis_OPEC.py",
        ROOT / "app" / "pages" / "15_Centro_OPEC.py",
    )

    for page in pages:
        source = page.read_text(encoding="utf-8")
        assert "opec_number=" in source, page.name
