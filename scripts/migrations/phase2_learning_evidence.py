"""Create the additive Phase 2 learning-evidence schema.

The command is a real dry-run by default: it inspects dependencies and reports
the exact tables that would be created without changing schema or data.  Only
``--apply`` performs writes, and it creates new tables with ``checkfirst``;
legacy tables are never altered or backfilled.

Examples::

    python scripts/migrations/phase2_learning_evidence.py
    python scripts/migrations/phase2_learning_evidence.py --apply
    python scripts/migrations/phase2_learning_evidence.py --database-url sqlite:///c:/tmp/test.db
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import Engine, create_engine, inspect


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.models import (  # noqa: E402
    ErrorEpisode,
    OpecLearningEvent,
    OpecLearningSession,
    OpecStudyPlan,
    OpecTopicState,
    StudyActivity,
)


PHASE2_TABLES = (
    OpecLearningSession.__table__,
    OpecLearningEvent.__table__,
    OpecTopicState.__table__,
    ErrorEpisode.__table__,
    OpecStudyPlan.__table__,
    StudyActivity.__table__,
)

# These are the only pre-existing tables referenced by the additive schema.
REQUIRED_TABLES = frozenset({
    "users",
    "competitions",
    "user_opec",
    "questions",
    "case_studies",
    "question_revisions",
    "source_documents",
})


class PreflightError(RuntimeError):
    """The destination cannot safely receive the Phase 2 tables."""


@dataclass(frozen=True)
class MigrationReport:
    applied: bool
    safe_to_apply: bool
    required_tables: tuple[str, ...]
    missing_required_tables: tuple[str, ...]
    phase2_tables_before: tuple[str, ...]
    tables_to_create: tuple[str, ...]
    phase2_tables_after: tuple[str, ...]
    tables_created: tuple[str, ...]

    def public_summary(self) -> dict:
        return asdict(self)


def _table_names(engine: Engine) -> set[str]:
    # Inspect a real connection.  This is reliable for SQLite ``:memory:`` and
    # avoids accidentally opening an unrelated connection during a test.
    with engine.connect() as connection:
        return set(inspect(connection).get_table_names())


def preflight(engine: Engine) -> MigrationReport:
    """Inspect the destination without writing schema or data."""

    existing = _table_names(engine)
    phase2_names = {table.name for table in PHASE2_TABLES}
    missing_required = tuple(sorted(REQUIRED_TABLES - existing))
    present_phase2 = tuple(sorted(phase2_names & existing))
    to_create = tuple(sorted(phase2_names - existing))
    return MigrationReport(
        applied=False,
        safe_to_apply=not missing_required,
        required_tables=tuple(sorted(REQUIRED_TABLES)),
        missing_required_tables=missing_required,
        phase2_tables_before=present_phase2,
        tables_to_create=to_create,
        phase2_tables_after=present_phase2,
        tables_created=(),
    )


def ensure_phase2_tables(engine: Engine) -> None:
    """Create only additive Phase 2 tables, in foreign-key order."""

    for table in PHASE2_TABLES:
        table.create(bind=engine, checkfirst=True)


def migrate(engine: Engine, *, apply: bool = False) -> MigrationReport:
    """Run a no-write preflight or explicitly create the additive schema."""

    before = preflight(engine)
    if not apply:
        return before
    if not before.safe_to_apply:
        raise PreflightError(
            "Faltan tablas requeridas; no se creó nada: "
            + ", ".join(before.missing_required_tables)
        )

    ensure_phase2_tables(engine)
    after_names = _table_names(engine)
    phase2_names = {table.name for table in PHASE2_TABLES}
    after = tuple(sorted(phase2_names & after_names))
    created = tuple(sorted(set(after) - set(before.phase2_tables_before)))
    return MigrationReport(
        applied=True,
        safe_to_apply=True,
        required_tables=before.required_tables,
        missing_required_tables=(),
        phase2_tables_before=before.phase2_tables_before,
        tables_to_create=before.tables_to_create,
        phase2_tables_after=after,
        tables_created=created,
    )


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def resolve_database_url(explicit_url: Optional[str]) -> str:
    if explicit_url:
        return _normalize_database_url(explicit_url)
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        return _normalize_database_url(configured)
    return f"sqlite:///{(PROJECT_ROOT / 'dian_sim.db').as_posix()}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Crea exclusivamente las tablas aditivas de Fase 2.",
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
