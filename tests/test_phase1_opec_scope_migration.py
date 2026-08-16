from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from db.models import (
    Base,
    CaseOpecScope,
    CaseStudy,
    Competition,
    OpecProfile,
    Question,
    QuestionCitation,
    QuestionOpecScope,
    QuestionRevision,
    SourceDocument,
)
from scripts.migrations.phase1_opec_scope import (
    PHASE1_TABLES,
    PreflightError,
    TARGET_COMPETITION_CODE,
    build_parser,
    demonstrated_case_catalog,
    migrate,
)


def _engine():
    return create_engine("sqlite+pysqlite:///:memory:")


def _question(*, question_id: str, competition_id: int, case_id: str, suffix: str):
    return Question(
        question_id=question_id,
        competition_id=competition_id,
        case_id=case_id,
        track="FUNCIONAL",
        competency="Aplicación",
        topic="Fiscalización",
        difficulty=2,
        question_type="SITUATIONAL",
        stem=f"Situación {suffix}",
        options_json={"A": "Correcta", "B": "Distractor", "C": "Distractor"},
        correct_key="A",
        rationale="Justificación",
        source_refs="Fuente pendiente",
        hash_norm=f"hash-{suffix}",
    )


def _seed_scope_fixture(engine, *, create_all: bool = True):
    if create_all:
        Base.metadata.create_all(engine)
    else:
        Base.metadata.create_all(
            engine,
            tables=[Competition.__table__, CaseStudy.__table__, Question.__table__],
        )

    demonstrated = demonstrated_case_catalog()[0]
    ambiguous_case_id = str(uuid.uuid4())
    with Session(engine) as session:
        competition = Competition(
            code=TARGET_COMPETITION_CODE,
            name="DIAN 2676 - Ingreso",
            entity="DIAN",
        )
        session.add(competition)
        session.flush()
        session.add_all(
            [
                CaseStudy(
                    id=demonstrated.case_id,
                    competition_id=competition.id,
                    title="Caso demostrado",
                    text="Situación laboral demostrada por CASE_FUNCTIONS.",
                    topic="Fiscalización",
                    difficulty=2,
                ),
                CaseStudy(
                    id=ambiguous_case_id,
                    competition_id=competition.id,
                    title="Caso ambiguo",
                    text="No tiene un identificador incluido en CASE_FUNCTIONS.",
                    topic="Fiscalización",
                    difficulty=2,
                ),
            ]
        )
        session.add_all(
            [
                _question(
                    question_id=str(uuid.uuid4()),
                    competition_id=competition.id,
                    case_id=demonstrated.case_id,
                    suffix="demostrada-1",
                ),
                _question(
                    question_id=str(uuid.uuid4()),
                    competition_id=competition.id,
                    case_id=demonstrated.case_id,
                    suffix="demostrada-2",
                ),
                _question(
                    question_id=str(uuid.uuid4()),
                    competition_id=competition.id,
                    case_id=ambiguous_case_id,
                    suffix="ambigua",
                ),
            ]
        )
        session.commit()
    return demonstrated, ambiguous_case_id


def test_dry_run_is_default_and_does_not_create_phase1_tables():
    engine = _engine()
    demonstrated, _ = _seed_scope_fixture(engine, create_all=False)

    assert build_parser().parse_args([]).apply is False
    result = migrate(engine)

    assert result.applied is False
    assert len(result.preflight.demonstrated_cases) == 1
    assert result.preflight.demonstrated_cases[0].case_id == demonstrated.case_id
    assert len(result.preflight.demonstrated_questions) == 2
    assert result.preflight.quarantined_case_count == 1
    assert result.preflight.quarantined_question_count == 1
    table_names = set(inspect(engine).get_table_names())
    assert not ({table.name for table in PHASE1_TABLES} & table_names)


def test_apply_refuses_to_create_empty_profile_when_corpus_is_absent():
    engine = _engine()
    Base.metadata.create_all(
        engine,
        tables=[Competition.__table__, CaseStudy.__table__, Question.__table__],
    )
    with Session(engine) as session:
        session.add(Competition(code=TARGET_COMPETITION_CODE, name="DIAN 2676"))
        session.commit()

    with pytest.raises(PreflightError, match="perfil OPEC vacío"):
        migrate(engine, apply=True)

    assert not ({table.name for table in PHASE1_TABLES} & set(inspect(engine).get_table_names()))


def test_apply_backfills_only_demonstrated_cases_and_is_idempotent():
    engine = _engine()
    demonstrated, ambiguous_case_id = _seed_scope_fixture(engine)

    dry_run = migrate(engine)
    with Session(engine) as session:
        assert session.scalar(select(OpecProfile.id)) is None
        assert session.scalar(select(CaseOpecScope.id)) is None
        assert session.scalar(select(QuestionOpecScope.id)) is None

    first = migrate(engine, apply=True)
    assert first.profile_created is True
    assert first.case_scopes_created == 1
    assert first.question_scopes_created == 2
    assert dry_run.preflight.quarantined_case_count == 1

    with Session(engine) as session:
        profile = session.scalar(select(OpecProfile))
        assert profile is not None
        assert profile.opec_number == "236769"
        case_scopes = tuple(session.scalars(select(CaseOpecScope)))
        question_scopes = tuple(session.scalars(select(QuestionOpecScope)))
        assert [scope.case_id for scope in case_scopes] == [demonstrated.case_id]
        assert case_scopes[0].function_number == demonstrated.function_number
        assert len(question_scopes) == 2
        assert {scope.function_number for scope in question_scopes} == {
            demonstrated.function_number
        }
        assert ambiguous_case_id not in {scope.case_id for scope in case_scopes}

    second = migrate(engine, apply=True)
    assert second.profile_created is False
    assert second.case_scopes_created == 0
    assert second.question_scopes_created == 0


def test_canonical_profile_and_scope_constraints_are_enforced():
    engine = _engine()
    demonstrated, _ = _seed_scope_fixture(engine)

    with Session(engine) as session:
        competition_id = session.scalar(
            select(Competition.id).where(Competition.code == TARGET_COMPETITION_CODE)
        )
        session.add_all(
            [
                OpecProfile(
                    competition_id=competition_id,
                    opec_number="236769",
                ),
                OpecProfile(
                    competition_id=competition_id,
                    opec_number="236769",
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()

    with Session(engine) as session:
        competition_id = session.scalar(
            select(Competition.id).where(Competition.code == TARGET_COMPETITION_CODE)
        )
        profile = OpecProfile(
            competition_id=competition_id,
            opec_number="236769",
        )
        session.add(profile)
        session.flush()
        session.add(
            CaseOpecScope(
                case_id=demonstrated.case_id,
                opec_profile_id=profile.id,
                function_number=0,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_citations_and_revisions_preserve_traceability_constraints():
    engine = _engine()
    demonstrated, _ = _seed_scope_fixture(engine)

    with Session(engine) as session:
        question_id = session.scalar(
            select(Question.question_id).where(Question.case_id == demonstrated.case_id)
        )
        source = SourceDocument(
            document_key="dian-et-vigente",
            title="Estatuto Tributario",
            entity="DIAN",
            document_type="estatuto",
            validity_status="current",
        )
        session.add(source)
        session.flush()
        session.add_all(
            [
                QuestionCitation(
                    question_id=question_id,
                    source_document_id=source.id,
                    locator="art. 746",
                ),
                QuestionRevision(
                    question_id=question_id,
                    revision_number=1,
                    content_hash="a" * 64,
                    stem="Versión uno",
                    options_json={"A": "Uno", "B": "Dos", "C": "Tres"},
                    correct_key="A",
                    status="approved",
                ),
            ]
        )
        session.commit()

        session.add(
            QuestionRevision(
                question_id=question_id,
                revision_number=1,
                content_hash="b" * 64,
                stem="Duplicada",
                options_json={"A": "Uno", "B": "Dos", "C": "Tres"},
                correct_key="A",
                status="candidate",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_phase1_ddl_keeps_likert_key_nullable_and_partition_constrained():
    revision_table = QuestionRevision.__table__
    scope_table = QuestionOpecScope.__table__

    assert revision_table.c.correct_key.nullable is True
    assert revision_table.c.bank_partition.nullable is False
    assert scope_table.c.bank_partition.nullable is False

    revision_checks = {
        constraint.name
        for constraint in revision_table.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }
    scope_checks = {
        constraint.name
        for constraint in scope_table.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_question_revision_partition" in revision_checks
    assert "ck_question_opec_scope_partition" in scope_checks

    postgres_ddl = str(
        CreateTable(revision_table).compile(dialect=postgresql.dialect())
    )
    sqlite_ddl = str(CreateTable(scope_table).compile(dialect=sqlite.dialect()))
    assert "correct_key VARCHAR(10) NOT NULL" not in postgres_ddl
    assert "correct_key VARCHAR(10)" in postgres_ddl
    for partition in ("training", "measurement", "anchor", "reserved"):
        assert f"'{partition}'" in postgres_ddl
        assert f"'{partition}'" in sqlite_ddl


@pytest.mark.parametrize(
    "partition",
    ["training", "measurement", "anchor", "reserved"],
)
@pytest.mark.parametrize("target", ["scope", "revision"])
def test_all_declared_bank_partitions_are_accepted(partition: str, target: str):
    engine = _engine()
    demonstrated, _ = _seed_scope_fixture(engine)

    with Session(engine) as session:
        competition_id = session.scalar(
            select(Competition.id).where(Competition.code == TARGET_COMPETITION_CODE)
        )
        question_id = session.scalar(
            select(Question.question_id).where(Question.case_id == demonstrated.case_id)
        )
        if target == "scope":
            profile = OpecProfile(
                competition_id=competition_id,
                opec_number="236769",
            )
            session.add(profile)
            session.flush()
            record = QuestionOpecScope(
                question_id=question_id,
                opec_profile_id=profile.id,
                function_number=demonstrated.function_number,
                bank_partition=partition,
            )
        else:
            record = QuestionRevision(
                question_id=question_id,
                revision_number=1,
                content_hash=f"{target}-{partition}",
                stem="Revisión con partición explícita",
                options_json={"A": "Uno", "B": "Dos", "C": "Tres"},
                correct_key="A",
                bank_partition=partition,
            )
        session.add(record)
        session.commit()
        session.refresh(record)
        assert record.bank_partition == partition


@pytest.mark.parametrize("target", ["scope", "revision"])
def test_unknown_bank_partition_is_rejected(target: str):
    engine = _engine()
    demonstrated, _ = _seed_scope_fixture(engine)

    with Session(engine) as session:
        competition_id = session.scalar(
            select(Competition.id).where(Competition.code == TARGET_COMPETITION_CODE)
        )
        question_id = session.scalar(
            select(Question.question_id).where(Question.case_id == demonstrated.case_id)
        )
        if target == "scope":
            profile = OpecProfile(
                competition_id=competition_id,
                opec_number="236769",
            )
            session.add(profile)
            session.flush()
            record = QuestionOpecScope(
                question_id=question_id,
                opec_profile_id=profile.id,
                bank_partition="public_exam",
            )
        else:
            record = QuestionRevision(
                question_id=question_id,
                revision_number=1,
                content_hash="invalid-partition",
                stem="Revisión inválida",
                options_json={"A": "Uno", "B": "Dos", "C": "Tres"},
                correct_key="A",
                bank_partition="public_exam",
            )
        session.add(record)
        with pytest.raises(IntegrityError):
            session.commit()


def test_likert_revision_can_be_persisted_without_correct_key():
    engine = _engine()
    demonstrated, _ = _seed_scope_fixture(engine)

    with Session(engine) as session:
        question = session.scalar(
            select(Question).where(Question.case_id == demonstrated.case_id)
        )
        question.question_type = "LIKERT"
        question.correct_key = None
        revision = QuestionRevision(
            question_id=question.question_id,
            revision_number=1,
            content_hash="likert-without-key",
            stem="Cuando trabajo bajo presión mantengo una conducta íntegra.",
            options_json={
                "1": "Totalmente en desacuerdo",
                "2": "En desacuerdo",
                "3": "De acuerdo",
                "4": "Totalmente de acuerdo",
            },
            correct_key=None,
            bank_partition="measurement",
            status="approved",
        )
        session.add(revision)
        session.commit()

        stored = session.get(QuestionRevision, revision.id)
        assert stored is not None
        assert stored.correct_key is None
        assert stored.bank_partition == "measurement"
