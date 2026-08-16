from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from core.legacy_question_audit import is_safe_for_active_study
from db.models import (
    Base,
    CaseOpecScope,
    CaseStudy,
    Competition,
    OpecProfile,
    Question,
    QuestionOpecScope,
)
from scripts.migrations.phase1_opec_scope import demonstrated_case_catalog
from scripts.migrations.reconcile_opec236769_snapshot import (
    ReconcileConflict,
    SnapshotValidationError,
    build_parser,
    load_snapshot,
    reconcile_snapshot,
)


LEGACY_TABLES = [Competition.__table__, CaseStudy.__table__, Question.__table__]


def _file_engine(path: Path):
    return create_engine(f"sqlite+pysqlite:///{path.as_posix()}")


def _source_question(logical_id: str, case_id: str, index: int, competition_id: int):
    question_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"{logical_id}:snapshot-question:{index}")
    )
    return Question(
        question_id=question_id,
        competition_id=competition_id,
        case_id=case_id,
        track="FUNCIONAL",
        competency="Fiscalización",
        topic=f"OPEC 236769 · Caso {logical_id}",
        macro_dominio="Fiscalización y liquidación",
        micro_competencia=f"OPEC 236769 F01 · {logical_id}",
        difficulty=(index % 3) + 1,
        question_type="SITUATIONAL",
        stem=f"SITUACIÓN {logical_id} · pregunta {index}",
        options_json={"A": "Correcta", "B": "Distractor", "C": "Distractor"},
        correct_key="A",
        rationale="Justificación histórica pendiente de nueva revisión.",
        source_refs="Estatuto Tributario · artículo por verificar",
        hash_norm=f"snapshot-hash-{logical_id}-{index}",
        is_verified=True,
        quality_report={
            "status": "APPROVED",
            "review": "human_source_grounded",
        },
    )


def _build_source(path: Path) -> Path:
    engine = _file_engine(path)
    Base.metadata.create_all(engine, tables=LEGACY_TABLES)
    with Session(engine) as session:
        competition = Competition(
            code="DIAN-2676",
            name="DIAN 2676 - Ingreso",
            entity="DIAN",
        )
        session.add(competition)
        session.flush()
        for item in demonstrated_case_catalog():
            session.add(
                CaseStudy(
                    id=item.case_id,
                    competition_id=competition.id,
                    title=f"Caso curado {item.logical_id}",
                    text=f"Situación laboral completa {item.logical_id}.",
                    difficulty=2,
                    topic="Fiscalización",
                )
            )
            session.add_all(
                [
                    _source_question(
                        item.logical_id,
                        item.case_id,
                        index,
                        competition.id,
                    )
                    for index in range(1, 4)
                ]
            )
        session.commit()
    engine.dispose()
    return path


def _build_destination(path: Path):
    engine = _file_engine(path)
    Base.metadata.create_all(engine, tables=LEGACY_TABLES)
    with Session(engine) as session:
        session.add(
            Competition(
                code="DIAN-2676",
                name="DIAN 2676 - Ingreso",
                entity="DIAN",
            )
        )
        session.commit()
    return engine


def _add_exact_record(session: Session, corpus, case_index: int = 0, question_index: int = 0):
    competition_id = session.scalar(
        select(Competition.id).where(Competition.code == "DIAN-2676")
    )
    case = corpus.cases[case_index]
    question = [item for item in corpus.questions if item.case_id == case.case_id][
        question_index
    ]
    session.add(
        CaseStudy(
            id=case.case_id,
            competition_id=competition_id,
            title=case.title,
            text=case.text,
            difficulty=case.difficulty,
            topic=case.topic,
        )
    )
    session.add(
        Question(
            question_id=question.question_id,
            competition_id=competition_id,
            case_id=question.case_id,
            track=question.track,
            competency=question.competency,
            topic=question.topic,
            macro_dominio=question.macro_dominio,
            micro_competencia=question.micro_competencia,
            difficulty=question.difficulty,
            question_type=question.question_type,
            stem=question.stem,
            options_json=question.options_json,
            correct_key=question.correct_key,
            rationale=question.rationale,
            source_refs=question.source_refs,
            hash_norm=question.hash_norm,
            is_verified=False,
            quality_report={"status": "PENDING_HUMAN_REVIEW"},
        )
    )


def test_dry_run_is_default_and_does_not_write_source_or_destination(tmp_path):
    source = _build_source(tmp_path / "source.db")
    destination = _build_destination(tmp_path / "destination.db")
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()

    assert build_parser().parse_args([]).apply is False
    report = reconcile_snapshot(source, destination)

    assert report.safe_to_apply is True
    assert report.source_cases == 48
    assert report.source_questions == 144
    assert report.cases_to_create == 48
    assert report.questions_to_create == 144
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_digest
    with Session(destination) as session:
        assert session.scalar(select(func.count()).select_from(CaseStudy)) == 0
        assert session.scalar(select(func.count()).select_from(Question)) == 0
    table_names = set(inspect(destination).get_table_names())
    assert "opec_profiles" not in table_names
    assert "question_opec_scopes" not in table_names
    destination.dispose()


def test_apply_imports_candidates_scopes_them_and_is_idempotent(tmp_path):
    source = _build_source(tmp_path / "source.db")
    destination = _build_destination(tmp_path / "destination.db")
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()

    first = reconcile_snapshot(source, destination, apply=True)

    assert first.applied is True
    assert first.cases_to_create == 48
    assert first.questions_to_create == 144
    assert first.case_scopes_created == 48
    assert first.question_scopes_created == 144
    assert first.profile_created is True
    with Session(destination) as session:
        questions = tuple(session.scalars(select(Question)))
        assert len(questions) == 144
        assert not any(question.is_verified for question in questions)
        assert not any(is_safe_for_active_study(question) for question in questions)
        assert {
            question.quality_report.get("status") for question in questions
        } == {"PENDING_HUMAN_REVIEW"}
        assert {
            question.quality_report.get("origin") for question in questions
        } == {"manual_question_review"}
        assert all(
            question.quality_report["import"]["historical_verified_ignored"]
            for question in questions
        )
        assert {
            question.quality_report["import"]["historical_status_ignored"]
            for question in questions
        } == {"APPROVED"}
        assert session.scalar(select(func.count()).select_from(OpecProfile)) == 1
        assert session.scalar(select(func.count()).select_from(CaseOpecScope)) == 48
        assert (
            session.scalar(select(func.count()).select_from(QuestionOpecScope))
            == 144
        )
        assert {
            row.bank_partition
            for row in session.scalars(select(QuestionOpecScope))
        } == {"training"}

    second = reconcile_snapshot(source, destination, apply=True)
    assert second.applied is True
    assert second.cases_to_create == 0
    assert second.questions_to_create == 0
    assert second.cases_to_skip == 48
    assert second.questions_to_skip == 144
    assert second.case_scopes_created == 0
    assert second.question_scopes_created == 0
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_digest
    destination.dispose()


def test_mixed_exact_destination_is_completed_without_overwrite(tmp_path):
    source = _build_source(tmp_path / "source.db")
    corpus = load_snapshot(source)
    destination = _build_destination(tmp_path / "destination.db")
    with Session(destination) as session:
        _add_exact_record(session, corpus)
        session.commit()

    dry_run = reconcile_snapshot(source, destination)
    assert dry_run.conflicts == ()
    assert dry_run.cases_to_skip == 1
    assert dry_run.questions_to_skip == 1
    assert dry_run.cases_to_create == 47
    assert dry_run.questions_to_create == 143

    applied = reconcile_snapshot(source, destination, apply=True)
    assert applied.applied is True
    with Session(destination) as session:
        assert session.scalar(select(func.count()).select_from(CaseStudy)) == 48
        assert session.scalar(select(func.count()).select_from(Question)) == 144
    destination.dispose()


@pytest.mark.parametrize("conflict_kind", ["case_id", "hash_norm"])
def test_conflicts_abort_without_partial_import_or_schema_write(tmp_path, conflict_kind):
    source = _build_source(tmp_path / "source.db")
    corpus = load_snapshot(source)
    destination = _build_destination(tmp_path / "destination.db")
    with Session(destination) as session:
        competition_id = session.scalar(
            select(Competition.id).where(Competition.code == "DIAN-2676")
        )
        first_case = corpus.cases[0]
        first_question = corpus.questions[0]
        if conflict_kind == "case_id":
            session.add(
                CaseStudy(
                    id=first_case.case_id,
                    competition_id=competition_id,
                    title="Contenido distinto",
                    text=first_case.text,
                    difficulty=first_case.difficulty,
                    topic=first_case.topic,
                )
            )
        else:
            legacy_case = CaseStudy(
                id="case-procedural-001",
                competition_id=competition_id,
                title="Caso legacy",
                text="No pertenece al corpus curado.",
                difficulty=2,
                topic="Legacy",
            )
            session.add(legacy_case)
            session.add(
                Question(
                    question_id=str(uuid.uuid4()),
                    competition_id=competition_id,
                    case_id=legacy_case.id,
                    track="FUNCIONAL",
                    competency="Legacy",
                    topic="Legacy",
                    difficulty=2,
                    question_type="SITUATIONAL",
                    stem="Colisión deliberada de hash.",
                    options_json={"A": "Uno", "B": "Dos", "C": "Tres"},
                    correct_key="A",
                    rationale="Prueba",
                    source_refs="Prueba",
                    hash_norm=first_question.hash_norm,
                    is_verified=False,
                )
            )
        session.commit()

    dry_run = reconcile_snapshot(source, destination)
    assert dry_run.safe_to_apply is False
    assert dry_run.conflicts
    with pytest.raises(ReconcileConflict):
        reconcile_snapshot(source, destination, apply=True)

    with Session(destination) as session:
        expected_ids = tuple(item.case_id for item in corpus.cases)
        imported_count = session.scalar(
            select(func.count()).select_from(CaseStudy).where(CaseStudy.id.in_(expected_ids))
        )
        assert imported_count == (1 if conflict_kind == "case_id" else 0)
    assert "opec_profiles" not in set(inspect(destination).get_table_names())
    destination.dispose()


def test_incomplete_source_is_rejected_before_destination_is_opened(tmp_path):
    source = _build_source(tmp_path / "source.db")
    source_engine = _file_engine(source)
    with source_engine.begin() as connection:
        question_id = connection.scalar(select(Question.question_id).limit(1))
        connection.execute(
            Question.__table__.delete().where(Question.question_id == question_id)
        )
    source_engine.dispose()
    destination = _build_destination(tmp_path / "destination.db")

    with pytest.raises(SnapshotValidationError, match="exactamente 3 preguntas"):
        reconcile_snapshot(source, destination)
    with Session(destination) as session:
        assert session.scalar(select(func.count()).select_from(CaseStudy)) == 0
    destination.dispose()
