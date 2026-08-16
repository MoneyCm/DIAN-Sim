"""Fase 1: identidad OPEC, alcance explícito y backfill conservador.

El comando es *dry-run* por defecto. Solo ``--apply`` crea las tablas aditivas
y persiste asociaciones. El backfill reconoce exclusivamente los UUID estables
derivados de ``core.opec_236769.CASE_FUNCTIONS``; título, tema, concurso activo
o similitud textual nunca se usan para inferir pertenencia.

Ejemplos::

    python scripts/migrations/phase1_opec_scope.py
    python scripts/migrations/phase1_opec_scope.py --apply
    python scripts/migrations/phase1_opec_scope.py --database-url sqlite:///c:/tmp/a.db
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import Engine, create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.opec_236769 import CASE_FUNCTIONS  # noqa: E402
from db.models import (  # noqa: E402
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


TARGET_COMPETITION_CODE = "DIAN-2676"
TARGET_OPEC_NUMBER = "236769"

PHASE1_TABLES = (
    OpecProfile.__table__,
    SourceDocument.__table__,
    QuestionOpecScope.__table__,
    CaseOpecScope.__table__,
    QuestionCitation.__table__,
    QuestionRevision.__table__,
)


class PreflightError(RuntimeError):
    """La base no satisface una precondición necesaria para migrar."""


@dataclass(frozen=True)
class ScopedCase:
    logical_id: str
    case_id: str
    function_number: int


@dataclass(frozen=True)
class ScopedQuestion:
    question_id: str
    case_id: str
    function_number: int


@dataclass(frozen=True)
class PreflightReport:
    competition_found: bool
    competition_id: Optional[int]
    expected_case_count: int
    demonstrated_cases: tuple[ScopedCase, ...]
    missing_case_ids: tuple[str, ...]
    conflicting_case_ids: tuple[str, ...]
    demonstrated_questions: tuple[ScopedQuestion, ...]
    question_competition_conflicts: tuple[str, ...]
    quarantined_case_count: int
    quarantined_question_count: int
    phase1_tables_present: bool
    existing_case_scope_count: int
    existing_question_scope_count: int
    unexpected_case_scope_count: int
    unexpected_question_scope_count: int

    def public_summary(self) -> dict:
        """Resumen serializable; conserva IDs para una auditoría reproducible."""

        data = asdict(self)
        data["demonstrated_case_count"] = len(self.demonstrated_cases)
        data["demonstrated_question_count"] = len(self.demonstrated_questions)
        return data


@dataclass(frozen=True)
class ApplyReport:
    applied: bool
    profile_created: bool
    case_scopes_created: int
    question_scopes_created: int
    case_scope_conflicts: int
    question_scope_conflicts: int
    preflight: PreflightReport

    def public_summary(self) -> dict:
        data = asdict(self)
        data["preflight"] = self.preflight.public_summary()
        return data


def _stable_case_id(logical_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, logical_id))


def demonstrated_case_catalog() -> tuple[ScopedCase, ...]:
    """Catálogo probado por código, independiente de etiquetas en la BD."""

    return tuple(
        ScopedCase(
            logical_id=logical_id,
            case_id=_stable_case_id(logical_id),
            function_number=int(function_number),
        )
        for logical_id, function_number in sorted(CASE_FUNCTIONS.items())
    )


def _require_legacy_tables(session: Session) -> set[str]:
    table_names = set(inspect(session.get_bind()).get_table_names())
    required = {"competitions", "case_studies", "questions"}
    missing = sorted(required - table_names)
    if missing:
        raise PreflightError(
            "Faltan tablas legacy requeridas: " + ", ".join(missing)
        )
    return table_names


def _existing_scope_state(
    session: Session,
    table_names: set[str],
    competition_id: int,
    demonstrated_case_ids: set[str],
    demonstrated_question_ids: set[str],
) -> tuple[int, int, int, int]:
    phase1_names = {table.name for table in PHASE1_TABLES}
    if not phase1_names.issubset(table_names):
        return 0, 0, 0, 0

    profile = session.scalar(
        select(OpecProfile).where(
            OpecProfile.competition_id == competition_id,
            OpecProfile.opec_number == TARGET_OPEC_NUMBER,
        )
    )
    if profile is None:
        return 0, 0, 0, 0

    case_ids = tuple(
        session.scalars(
            select(CaseOpecScope.case_id).where(
                CaseOpecScope.opec_profile_id == profile.id
            )
        )
    )
    question_ids = tuple(
        session.scalars(
            select(QuestionOpecScope.question_id).where(
                QuestionOpecScope.opec_profile_id == profile.id
            )
        )
    )
    return (
        sum(case_id in demonstrated_case_ids for case_id in case_ids),
        sum(question_id in demonstrated_question_ids for question_id in question_ids),
        sum(case_id not in demonstrated_case_ids for case_id in case_ids),
        sum(question_id not in demonstrated_question_ids for question_id in question_ids),
    )


def preflight(session: Session) -> PreflightReport:
    """Inspecciona sin escribir y separa evidencia, conflictos y cuarentena."""

    table_names = _require_legacy_tables(session)
    catalog = demonstrated_case_catalog()
    expected_by_id = {item.case_id: item for item in catalog}

    competition = session.scalar(
        select(Competition).where(Competition.code == TARGET_COMPETITION_CODE)
    )
    if competition is None:
        return PreflightReport(
            competition_found=False,
            competition_id=None,
            expected_case_count=len(catalog),
            demonstrated_cases=(),
            missing_case_ids=tuple(item.case_id for item in catalog),
            conflicting_case_ids=(),
            demonstrated_questions=(),
            question_competition_conflicts=(),
            quarantined_case_count=0,
            quarantined_question_count=0,
            phase1_tables_present={table.name for table in PHASE1_TABLES}.issubset(
                table_names
            ),
            existing_case_scope_count=0,
            existing_question_scope_count=0,
            unexpected_case_scope_count=0,
            unexpected_question_scope_count=0,
        )

    expected_rows = session.execute(
        select(CaseStudy.id, CaseStudy.competition_id).where(
            CaseStudy.id.in_(tuple(expected_by_id))
        )
    ).all()
    row_competition = {str(case_id): competition_id for case_id, competition_id in expected_rows}

    demonstrated_cases = tuple(
        item
        for item in catalog
        if row_competition.get(item.case_id) == competition.id
    )
    demonstrated_ids = {item.case_id for item in demonstrated_cases}
    missing_case_ids = tuple(
        item.case_id for item in catalog if item.case_id not in row_competition
    )
    conflicting_case_ids = tuple(
        item.case_id
        for item in catalog
        if item.case_id in row_competition
        and row_competition[item.case_id] != competition.id
    )

    target_cases = set(
        session.scalars(
            select(CaseStudy.id).where(CaseStudy.competition_id == competition.id)
        )
    )
    quarantined_case_ids = target_cases - demonstrated_ids

    case_function = {
        item.case_id: item.function_number for item in demonstrated_cases
    }
    demonstrated_questions: list[ScopedQuestion] = []
    question_competition_conflicts: list[str] = []
    quarantined_question_count = 0
    questions = session.execute(
        select(Question.question_id, Question.case_id, Question.competition_id).where(
            (Question.competition_id == competition.id)
            | Question.case_id.in_(tuple(demonstrated_ids))
        )
    ).all()
    for question_id, case_id, question_competition_id in questions:
        if case_id in demonstrated_ids and question_competition_id == competition.id:
            demonstrated_questions.append(
                ScopedQuestion(
                    question_id=str(question_id),
                    case_id=str(case_id),
                    function_number=case_function[str(case_id)],
                )
            )
        elif case_id in demonstrated_ids:
            question_competition_conflicts.append(str(question_id))
        elif question_competition_id == competition.id:
            # Incluye preguntas sin caso y casos no demostrados. Permanecen sin
            # alcance explícito: esta es la cuarentena conservadora de Fase 1.
            quarantined_question_count += 1

    demonstrated_questions_tuple = tuple(
        sorted(demonstrated_questions, key=lambda item: item.question_id)
    )
    demonstrated_question_ids = {
        item.question_id for item in demonstrated_questions_tuple
    }
    existing_state = _existing_scope_state(
        session,
        table_names,
        competition.id,
        demonstrated_ids,
        demonstrated_question_ids,
    )

    return PreflightReport(
        competition_found=True,
        competition_id=competition.id,
        expected_case_count=len(catalog),
        demonstrated_cases=demonstrated_cases,
        missing_case_ids=missing_case_ids,
        conflicting_case_ids=conflicting_case_ids,
        demonstrated_questions=demonstrated_questions_tuple,
        question_competition_conflicts=tuple(sorted(question_competition_conflicts)),
        quarantined_case_count=len(quarantined_case_ids),
        quarantined_question_count=quarantined_question_count,
        phase1_tables_present={table.name for table in PHASE1_TABLES}.issubset(
            table_names
        ),
        existing_case_scope_count=existing_state[0],
        existing_question_scope_count=existing_state[1],
        unexpected_case_scope_count=existing_state[2],
        unexpected_question_scope_count=existing_state[3],
    )


def ensure_phase1_tables(engine: Engine) -> None:
    """Crea únicamente las tablas nuevas; nunca altera tablas legacy."""

    for table in PHASE1_TABLES:
        table.create(bind=engine, checkfirst=True)


def _scope_conflict(existing_function: Optional[int], expected_function: int) -> bool:
    return existing_function is not None and existing_function != expected_function


def validate_preflight_for_apply(report: PreflightReport) -> None:
    """Fail before any schema write when the demonstrated corpus is unsafe."""
    if not report.competition_found or report.competition_id is None:
        raise PreflightError(
            f"No existe el concurso exacto {TARGET_COMPETITION_CODE}; no se aplicó nada."
        )
    if not report.demonstrated_cases or not report.demonstrated_questions:
        raise PreflightError(
            "El preflight no encontró casos y preguntas demostrables de CASE_FUNCTIONS. "
            "No se creará un perfil OPEC vacío; carga o identifica el corpus correcto "
            "antes de aplicar la migración."
        )
    if report.conflicting_case_ids or report.question_competition_conflicts:
        raise PreflightError(
            "Hay IDs demostrados asociados a otro concurso. Corrige esos conflictos "
            "antes de aplicar el backfill."
        )
    if report.unexpected_case_scope_count or report.unexpected_question_scope_count:
        raise PreflightError(
            "Ya existen alcances 236769 no respaldados por CASE_FUNCTIONS. "
            "Se requiere revisión explícita; el migrador no los borra ni los valida."
        )


def apply_backfill(session: Session, report: PreflightReport) -> ApplyReport:
    """Persiste solo asociaciones demostradas y es idempotente."""

    validate_preflight_for_apply(report)

    profile = session.scalar(
        select(OpecProfile).where(
            OpecProfile.competition_id == report.competition_id,
            OpecProfile.opec_number == TARGET_OPEC_NUMBER,
        )
    )
    profile_created = profile is None
    if profile is None:
        profile = OpecProfile(
            competition_id=report.competition_id,
            opec_number=TARGET_OPEC_NUMBER,
            source_status="scope_mapping_only",
            source_version="CASE_FUNCTIONS",
        )
        session.add(profile)
        session.flush()

    existing_case_scopes = {
        row.case_id: row
        for row in session.scalars(
            select(CaseOpecScope).where(
                CaseOpecScope.opec_profile_id == profile.id
            )
        )
    }
    case_created = 0
    case_conflicts = 0
    for item in report.demonstrated_cases:
        existing = existing_case_scopes.get(item.case_id)
        if existing is not None:
            case_conflicts += int(
                _scope_conflict(existing.function_number, item.function_number)
            )
            continue
        session.add(
            CaseOpecScope(
                case_id=item.case_id,
                opec_profile_id=profile.id,
                function_number=item.function_number,
                scope_kind="primary",
            )
        )
        case_created += 1

    existing_question_scopes = {
        row.question_id: row
        for row in session.scalars(
            select(QuestionOpecScope).where(
                QuestionOpecScope.opec_profile_id == profile.id
            )
        )
    }
    question_created = 0
    question_conflicts = 0
    for item in report.demonstrated_questions:
        existing = existing_question_scopes.get(item.question_id)
        if existing is not None:
            question_conflicts += int(
                _scope_conflict(existing.function_number, item.function_number)
            )
            continue
        session.add(
            QuestionOpecScope(
                question_id=item.question_id,
                opec_profile_id=profile.id,
                function_number=item.function_number,
                scope_kind="primary",
            )
        )
        question_created += 1

    session.flush()
    return ApplyReport(
        applied=True,
        profile_created=profile_created,
        case_scopes_created=case_created,
        question_scopes_created=question_created,
        case_scope_conflicts=case_conflicts,
        question_scope_conflicts=question_conflicts,
        preflight=report,
    )


def migrate(engine: Engine, *, apply: bool = False) -> ApplyReport:
    """Ejecuta dry-run o aplicación explícita sobre un engine."""
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        report = preflight(session)
        if not apply:
            session.rollback()
            return ApplyReport(
                applied=False,
                profile_created=False,
                case_scopes_created=0,
                question_scopes_created=0,
                case_scope_conflicts=0,
                question_scope_conflicts=0,
                preflight=report,
            )

        # Validate against legacy tables before creating even the additive
        # schema, so a wrong/empty database remains completely untouched.
        validate_preflight_for_apply(report)

    ensure_phase1_tables(engine)

    with session_factory() as session:
        report = preflight(session)
        result = apply_backfill(session, report)
        session.commit()
        return result


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def resolve_database_url(explicit_url: Optional[str]) -> str:
    if explicit_url:
        return _normalize_database_url(explicit_url)
    configured = os.getenv("DATABASE_URL")
    if configured:
        return _normalize_database_url(configured)
    return f"sqlite:///{(PROJECT_ROOT / 'dian_sim.db').as_posix()}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Crea las tablas aditivas y persiste el backfill demostrado.",
    )
    parser.add_argument(
        "--database-url",
        help="URL explícita. Por defecto usa DATABASE_URL o dian_sim.db local.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    engine = create_engine(resolve_database_url(args.database_url), pool_pre_ping=True)
    try:
        result = migrate(engine, apply=args.apply)
    except PreflightError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    finally:
        engine.dispose()

    print(
        json.dumps(
            {"ok": True, **result.public_summary()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
