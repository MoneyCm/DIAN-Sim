"""Importa de forma conservadora el corpus curado OPEC 236769.

La fuente es un archivo SQLite abierto siempre en modo de solo lectura. El
destino se inspecciona en *dry-run* por defecto; únicamente ``--apply`` inserta
contenido y crea sus alcances canónicos de Fase 1.

No se usan títulos, temas ni similitud textual para decidir pertenencia. El
conjunto permitido son los 48 UUID5 derivados de ``CASE_FUNCTIONS`` y las tres
preguntas que la fuente relaciona con cada uno (144 en total).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import Engine, create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.question_review import MANUAL_QUESTION_REVIEW  # noqa: E402
from db.models import CaseStudy, Competition, Question  # noqa: E402
from scripts.migrations.phase1_opec_scope import (  # noqa: E402
    TARGET_COMPETITION_CODE,
    apply_backfill as apply_scope_backfill,
    demonstrated_case_catalog,
    ensure_phase1_tables,
    preflight as scope_preflight,
)


EXPECTED_CASE_COUNT = 48
EXPECTED_QUESTION_COUNT = 144
IMPORT_VERSION = "opec236769-snapshot-v1"


class SnapshotValidationError(RuntimeError):
    """La fuente no contiene exactamente el corpus permitido."""


class ReconcileConflict(RuntimeError):
    """El destino contiene una colisión que el importador no debe resolver."""

    def __init__(self, report: "ReconcileReport"):
        self.report = report
        super().__init__(
            "El destino contiene conflictos de ID, hash o contenido; no se escribió nada."
        )


@dataclass(frozen=True)
class SnapshotCase:
    case_id: str
    title: Optional[str]
    text: str
    difficulty: int
    topic: str


@dataclass(frozen=True)
class SnapshotQuestion:
    question_id: str
    case_id: str
    track: str
    competency: str
    topic: str
    macro_dominio: Optional[str]
    micro_competencia: Optional[str]
    difficulty: int
    question_type: str
    stem: str
    options_json: dict
    correct_key: Optional[str]
    rationale: Optional[str]
    source_refs: Optional[str]
    hash_norm: str
    historical_verified: bool
    historical_status: Optional[str]


@dataclass(frozen=True)
class SnapshotCorpus:
    source_name: str
    cases: tuple[SnapshotCase, ...]
    questions: tuple[SnapshotQuestion, ...]


@dataclass(frozen=True)
class ReconcileReport:
    source_cases: int
    source_questions: int
    cases_to_create: int
    questions_to_create: int
    cases_to_skip: int
    questions_to_skip: int
    conflicts: tuple[str, ...]
    applied: bool = False
    case_scopes_created: int = 0
    question_scopes_created: int = 0
    profile_created: bool = False

    @property
    def safe_to_apply(self) -> bool:
        return not self.conflicts

    def public_summary(self) -> dict:
        return {**asdict(self), "safe_to_apply": self.safe_to_apply}


def _decode_json(value, *, field: str, identifier: str) -> dict:
    if isinstance(value, dict):
        decoded = value
    else:
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise SnapshotValidationError(
                f"JSON inválido en {field} de {identifier}."
            ) from exc
    if not isinstance(decoded, dict):
        raise SnapshotValidationError(
            f"{field} de {identifier} debe ser un objeto JSON."
        )
    return decoded


def _optional_json(value) -> dict:
    if not value:
        return {}
    try:
        decoded = json.loads(value) if not isinstance(value, dict) else value
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _required_columns(connection: sqlite3.Connection, table: str, required: set[str]) -> None:
    columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
    missing = sorted(required - columns)
    if missing:
        raise SnapshotValidationError(
            f"La tabla fuente {table} carece de columnas: {', '.join(missing)}."
        )


def load_snapshot(source_path: Path | str) -> SnapshotCorpus:
    """Lee y valida el corpus permitido sin abrir la fuente para escritura."""

    path = Path(source_path).expanduser().resolve()
    if not path.is_file():
        raise SnapshotValidationError(f"No existe la fuente SQLite: {path}")

    uri = f"file:{path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _required_columns(
            connection,
            "competitions",
            {"id", "code"},
        )
        _required_columns(
            connection,
            "case_studies",
            {"id", "competition_id", "title", "text", "difficulty", "topic"},
        )
        _required_columns(
            connection,
            "questions",
            {
                "question_id",
                "competition_id",
                "case_id",
                "track",
                "competency",
                "topic",
                "macro_dominio",
                "micro_competencia",
                "difficulty",
                "question_type",
                "stem",
                "options_json",
                "correct_key",
                "rationale",
                "source_refs",
                "hash_norm",
                "is_verified",
                "quality_report",
            },
        )

        competitions = connection.execute(
            "SELECT id FROM competitions WHERE code = ?",
            (TARGET_COMPETITION_CODE,),
        ).fetchall()
        if len(competitions) != 1:
            raise SnapshotValidationError(
                f"La fuente debe contener un único concurso {TARGET_COMPETITION_CODE}."
            )
        competition_id = competitions[0]["id"]

        cases: list[SnapshotCase] = []
        questions: list[SnapshotQuestion] = []
        seen_question_ids: set[str] = set()
        seen_hashes: set[str] = set()
        for catalog_item in demonstrated_case_catalog():
            case_rows = connection.execute(
                "SELECT id, competition_id, title, text, difficulty, topic "
                "FROM case_studies WHERE id = ?",
                (catalog_item.case_id,),
            ).fetchall()
            if len(case_rows) != 1:
                raise SnapshotValidationError(
                    f"Falta o está duplicado el caso esperado {catalog_item.case_id}."
                )
            case_row = case_rows[0]
            if case_row["competition_id"] != competition_id:
                raise SnapshotValidationError(
                    f"El caso {catalog_item.case_id} pertenece a otro concurso."
                )
            cases.append(
                SnapshotCase(
                    case_id=str(case_row["id"]),
                    title=case_row["title"],
                    text=str(case_row["text"]),
                    difficulty=int(case_row["difficulty"]),
                    topic=str(case_row["topic"]),
                )
            )

            question_rows = connection.execute(
                "SELECT question_id, competition_id, case_id, track, competency, topic, "
                "macro_dominio, micro_competencia, difficulty, question_type, stem, "
                "options_json, correct_key, rationale, source_refs, hash_norm, "
                "is_verified, quality_report "
                "FROM questions WHERE case_id = ? ORDER BY question_id",
                (catalog_item.case_id,),
            ).fetchall()
            if len(question_rows) != 3:
                raise SnapshotValidationError(
                    f"El caso {catalog_item.case_id} debe tener exactamente 3 preguntas; "
                    f"se encontraron {len(question_rows)}."
                )
            for row in question_rows:
                question_id = str(row["question_id"])
                hash_norm = str(row["hash_norm"] or "").strip()
                if not hash_norm:
                    raise SnapshotValidationError(
                        f"La pregunta {question_id} no tiene hash_norm."
                    )
                if question_id in seen_question_ids:
                    raise SnapshotValidationError(
                        f"ID de pregunta duplicado en fuente: {question_id}."
                    )
                if hash_norm in seen_hashes:
                    raise SnapshotValidationError(
                        f"hash_norm duplicado en fuente: {hash_norm}."
                    )
                if row["competition_id"] != competition_id:
                    raise SnapshotValidationError(
                        f"La pregunta {question_id} pertenece a otro concurso."
                    )
                if str(row["case_id"]) != catalog_item.case_id:
                    raise SnapshotValidationError(
                        f"La pregunta {question_id} tiene una FK de caso inconsistente."
                    )
                seen_question_ids.add(question_id)
                seen_hashes.add(hash_norm)
                historical_report = _optional_json(row["quality_report"])
                questions.append(
                    SnapshotQuestion(
                        question_id=question_id,
                        case_id=catalog_item.case_id,
                        track=str(row["track"]),
                        competency=str(row["competency"]),
                        topic=str(row["topic"]),
                        macro_dominio=row["macro_dominio"],
                        micro_competencia=row["micro_competencia"],
                        difficulty=int(row["difficulty"]),
                        question_type=str(row["question_type"] or "SITUATIONAL"),
                        stem=str(row["stem"]),
                        options_json=_decode_json(
                            row["options_json"],
                            field="options_json",
                            identifier=question_id,
                        ),
                        correct_key=row["correct_key"],
                        rationale=row["rationale"],
                        source_refs=row["source_refs"],
                        hash_norm=hash_norm,
                        historical_verified=bool(row["is_verified"]),
                        historical_status=historical_report.get("status"),
                    )
                )

        if len(cases) != EXPECTED_CASE_COUNT or len(questions) != EXPECTED_QUESTION_COUNT:
            raise SnapshotValidationError(
                "La fuente no coincide con el inventario cerrado de 48 casos y 144 preguntas."
            )
        return SnapshotCorpus(path.name, tuple(cases), tuple(questions))
    except sqlite3.DatabaseError as exc:
        raise SnapshotValidationError(f"No se pudo validar la fuente SQLite: {exc}") from exc
    finally:
        connection.close()


def _question_signature(question) -> tuple:
    options = question.options_json
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except ValueError:
            pass
    return (
        str(question.case_id),
        str(question.track),
        str(question.competency),
        str(question.topic),
        question.macro_dominio,
        question.micro_competencia,
        int(question.difficulty),
        str(question.question_type or "SITUATIONAL"),
        str(question.stem),
        options,
        question.correct_key,
        question.rationale,
        question.source_refs,
        str(question.hash_norm),
    )


def _snapshot_question_signature(question: SnapshotQuestion) -> tuple:
    return (
        question.case_id,
        question.track,
        question.competency,
        question.topic,
        question.macro_dominio,
        question.micro_competencia,
        question.difficulty,
        question.question_type,
        question.stem,
        question.options_json,
        question.correct_key,
        question.rationale,
        question.source_refs,
        question.hash_norm,
    )


def inspect_destination(session: Session, corpus: SnapshotCorpus) -> ReconcileReport:
    """Calcula inserciones y colisiones sin modificar el destino."""

    table_names = set(inspect(session.get_bind()).get_table_names())
    required = {"competitions", "case_studies", "questions"}
    missing = sorted(required - table_names)
    if missing:
        raise ReconcileConflict(
            ReconcileReport(
                len(corpus.cases),
                len(corpus.questions),
                0,
                0,
                0,
                0,
                ("tablas destino ausentes: " + ", ".join(missing),),
            )
        )

    competitions = tuple(
        session.scalars(
            select(Competition).where(Competition.code == TARGET_COMPETITION_CODE)
        )
    )
    if len(competitions) != 1:
        return ReconcileReport(
            len(corpus.cases),
            len(corpus.questions),
            0,
            0,
            0,
            0,
            (f"concurso destino {TARGET_COMPETITION_CODE} ausente o duplicado",),
        )
    competition = competitions[0]

    case_ids = tuple(item.case_id for item in corpus.cases)
    existing_cases = {
        item.id: item
        for item in session.scalars(select(CaseStudy).where(CaseStudy.id.in_(case_ids)))
    }
    question_ids = tuple(item.question_id for item in corpus.questions)
    existing_questions = {
        item.question_id: item
        for item in session.scalars(
            select(Question).where(Question.question_id.in_(question_ids))
        )
    }
    hashes = tuple(item.hash_norm for item in corpus.questions)
    hash_owners = {
        item.hash_norm: item.question_id
        for item in session.scalars(select(Question).where(Question.hash_norm.in_(hashes)))
    }

    conflicts: list[str] = []
    cases_to_create = cases_to_skip = 0
    for item in corpus.cases:
        existing = existing_cases.get(item.case_id)
        if existing is None:
            cases_to_create += 1
            continue
        expected = (item.title, item.text, item.difficulty, item.topic)
        actual = (existing.title, existing.text, existing.difficulty, existing.topic)
        if existing.competition_id != competition.id:
            conflicts.append(f"case_id en otro concurso: {item.case_id}")
        elif actual != expected:
            conflicts.append(f"case_id con contenido diferente: {item.case_id}")
        else:
            cases_to_skip += 1

    questions_to_create = questions_to_skip = 0
    for item in corpus.questions:
        existing = existing_questions.get(item.question_id)
        hash_owner = hash_owners.get(item.hash_norm)
        if hash_owner is not None and hash_owner != item.question_id:
            conflicts.append(
                f"hash_norm {item.hash_norm} ya pertenece a {hash_owner}"
            )
        if existing is None:
            questions_to_create += 1
            continue
        if existing.competition_id != competition.id:
            conflicts.append(f"question_id en otro concurso: {item.question_id}")
        elif _question_signature(existing) != _snapshot_question_signature(item):
            conflicts.append(f"question_id con contenido diferente: {item.question_id}")
        else:
            questions_to_skip += 1

    return ReconcileReport(
        source_cases=len(corpus.cases),
        source_questions=len(corpus.questions),
        cases_to_create=cases_to_create,
        questions_to_create=questions_to_create,
        cases_to_skip=cases_to_skip,
        questions_to_skip=questions_to_skip,
        conflicts=tuple(sorted(set(conflicts))),
    )


def _candidate_report(item: SnapshotQuestion, source_name: str) -> dict:
    return {
        "status": "PENDING_HUMAN_REVIEW",
        "review": "snapshot_import_candidate",
        "origin": MANUAL_QUESTION_REVIEW,
        "import": {
            "version": IMPORT_VERSION,
            "source_file": source_name,
            "historical_verified_ignored": item.historical_verified,
            "historical_status_ignored": item.historical_status,
        },
    }


def _insert_planned(
    session: Session,
    corpus: SnapshotCorpus,
    report: ReconcileReport,
) -> None:
    competition = session.scalar(
        select(Competition).where(Competition.code == TARGET_COMPETITION_CODE)
    )
    existing_case_ids = set(
        session.scalars(
            select(CaseStudy.id).where(
                CaseStudy.id.in_(tuple(item.case_id for item in corpus.cases))
            )
        )
    )
    for item in corpus.cases:
        if item.case_id in existing_case_ids:
            continue
        session.add(
            CaseStudy(
                id=item.case_id,
                competition_id=competition.id,
                title=item.title,
                text=item.text,
                difficulty=item.difficulty,
                topic=item.topic,
            )
        )
    session.flush()

    existing_question_ids = set(
        session.scalars(
            select(Question.question_id).where(
                Question.question_id.in_(
                    tuple(item.question_id for item in corpus.questions)
                )
            )
        )
    )
    for item in corpus.questions:
        if item.question_id in existing_question_ids:
            continue
        session.add(
            Question(
                question_id=item.question_id,
                competition_id=competition.id,
                case_id=item.case_id,
                track=item.track,
                competency=item.competency,
                topic=item.topic,
                macro_dominio=item.macro_dominio,
                micro_competencia=item.micro_competencia,
                difficulty=item.difficulty,
                question_type=item.question_type,
                stem=item.stem,
                options_json=item.options_json,
                correct_key=item.correct_key,
                rationale=item.rationale,
                source_refs=item.source_refs,
                hash_norm=item.hash_norm,
                is_verified=False,
                quality_report=_candidate_report(item, corpus.source_name),
                global_hits=0,
                global_misses=0,
            )
        )
    session.flush()


def _same_sqlite_file(source_path: Path, engine: Engine) -> bool:
    if engine.dialect.name != "sqlite" or engine.url.database in (None, ":memory:"):
        return False
    return source_path.resolve() == Path(engine.url.database).expanduser().resolve()


def reconcile_snapshot(
    source_path: Path | str,
    destination_engine: Engine,
    *,
    apply: bool = False,
) -> ReconcileReport:
    """Planifica o importa el snapshot; nunca modifica la fuente."""

    source = Path(source_path).expanduser().resolve()
    if _same_sqlite_file(source, destination_engine):
        raise SnapshotValidationError("Fuente y destino no pueden ser el mismo archivo.")
    corpus = load_snapshot(source)
    session_factory = sessionmaker(bind=destination_engine, expire_on_commit=False)
    with session_factory() as session:
        report = inspect_destination(session, corpus)
        session.rollback()
    if not apply:
        return report
    if report.conflicts:
        raise ReconcileConflict(report)

    # Se crean únicamente tablas aditivas después de validar fuente y destino.
    ensure_phase1_tables(destination_engine)
    with session_factory() as session:
        # Repetir el preflight dentro de la transacción reduce el riesgo de una
        # colisión aparecida entre el dry-run y la escritura.
        report = inspect_destination(session, corpus)
        if report.conflicts:
            session.rollback()
            raise ReconcileConflict(report)
        _insert_planned(session, corpus, report)

        scope_report = scope_preflight(session)
        scope_result = apply_scope_backfill(session, scope_report)
        session.commit()
        return replace(
            report,
            applied=True,
            case_scopes_created=scope_result.case_scopes_created,
            question_scopes_created=scope_result.question_scopes_created,
            profile_created=scope_result.profile_created,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str(PROJECT_ROOT / "dian_sim_opec236769.db"),
        help="Snapshot SQLite fuente; siempre se abre en modo de solo lectura.",
    )
    parser.add_argument(
        "--destination-url",
        default=f"sqlite:///{(PROJECT_ROOT / 'dian_sim.db').as_posix()}",
        help="URL SQLAlchemy del destino. No se hereda DATABASE_URL.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Importa candidatos y aplica sus alcances OPEC de Fase 1.",
    )
    return parser


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    destination_engine = create_engine(
        _normalize_database_url(args.destination_url),
        pool_pre_ping=True,
    )
    try:
        report = reconcile_snapshot(
            args.source,
            destination_engine,
            apply=args.apply,
        )
    except ReconcileConflict as exc:
        print(
            json.dumps(
                {"ok": False, "error": str(exc), **exc.report.public_summary()},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    except SnapshotValidationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    finally:
        destination_engine.dispose()

    print(
        json.dumps(
            {"ok": report.safe_to_apply, **report.public_summary()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report.safe_to_apply else 2


if __name__ == "__main__":
    raise SystemExit(main())
