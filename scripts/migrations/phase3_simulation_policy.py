"""Create the additive Phase 3 OPEC simulation-policy schema.

The command only inspects by default. ``--apply`` explicitly creates the new
table and never alters or backfills an existing table.

Examples::

    python scripts/migrations/phase3_simulation_policy.py
    python scripts/migrations/phase3_simulation_policy.py --apply
    python scripts/migrations/phase3_simulation_policy.py --database-url sqlite:///c:/tmp/test.db
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
from typing import Iterable, Optional

from sqlalchemy import (
    Engine,
    ForeignKeyConstraint,
    UniqueConstraint,
    create_engine,
    inspect,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.models import OpecSimulationPolicy  # noqa: E402


PHASE3_TABLES = (OpecSimulationPolicy.__table__,)
REQUIRED_TABLES = frozenset({"competitions", "opec_profiles"})


class PreflightError(RuntimeError):
    """The destination cannot safely receive the Phase 3 table."""


@dataclass(frozen=True)
class MigrationReport:
    applied: bool
    safe_to_apply: bool
    required_tables: tuple[str, ...]
    missing_required_tables: tuple[str, ...]
    phase3_tables_before: tuple[str, ...]
    tables_to_create: tuple[str, ...]
    incompatible_tables: tuple[str, ...]
    phase3_tables_after: tuple[str, ...]
    tables_created: tuple[str, ...]

    def public_summary(self) -> dict:
        return asdict(self)


def _table_is_compatible(inspector, table) -> bool:
    actual_columns = {
        column["name"]: column for column in inspector.get_columns(table.name)
    }
    if not {column.name for column in table.columns}.issubset(actual_columns):
        return False
    if any(
        not column.nullable and actual_columns[column.name].get("nullable", True)
        for column in table.columns
        if not column.primary_key
    ):
        return False
    expected_pk = tuple(column.name for column in table.primary_key.columns)
    actual_pk = tuple(inspector.get_pk_constraint(table.name).get("constrained_columns") or ())
    if expected_pk != actual_pk:
        return False

    expected_uniques = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    actual_uniques = {
        tuple(item.get("column_names") or ())
        for item in inspector.get_unique_constraints(table.name)
    }
    if not expected_uniques.issubset(actual_uniques):
        return False

    expected_fks = {
        (
            tuple(column.name for column in constraint.columns),
            constraint.referred_table.name,
            tuple(element.column.name for element in constraint.elements),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    actual_fks = {
        (
            tuple(item.get("constrained_columns") or ()),
            item.get("referred_table"),
            tuple(item.get("referred_columns") or ()),
        )
        for item in inspector.get_foreign_keys(table.name)
    }
    return expected_fks.issubset(actual_fks)


def _schema_snapshot(engine: Engine) -> tuple[set[str], dict[str, set[str]], set[str]]:
    with engine.connect() as connection:
        inspector = inspect(connection)
        names = set(inspector.get_table_names())
        columns = {
            table.name: {
                column["name"] for column in inspector.get_columns(table.name)
            }
            for table in PHASE3_TABLES
            if table.name in names
        }
        incompatible = {
            table.name
            for table in PHASE3_TABLES
            if table.name in names and not _table_is_compatible(inspector, table)
        }
    return names, columns, incompatible


def preflight(engine: Engine) -> MigrationReport:
    """Inspect dependencies and any pre-existing Phase 3 table without writes."""

    existing, _existing_columns, incompatible_names = _schema_snapshot(engine)
    phase3_names = {table.name for table in PHASE3_TABLES}
    missing_required = tuple(sorted(REQUIRED_TABLES - existing))
    present = tuple(sorted(phase3_names & existing))
    to_create = tuple(sorted(phase3_names - existing))
    incompatible = tuple(sorted(incompatible_names))
    return MigrationReport(
        applied=False,
        safe_to_apply=not missing_required and not incompatible,
        required_tables=tuple(sorted(REQUIRED_TABLES)),
        missing_required_tables=missing_required,
        phase3_tables_before=present,
        tables_to_create=to_create,
        incompatible_tables=incompatible,
        phase3_tables_after=present,
        tables_created=(),
    )


def ensure_phase3_tables(engine: Engine) -> None:
    """Create only the additive simulation-policy table."""

    with engine.begin() as connection:
        for table in PHASE3_TABLES:
            table.create(bind=connection, checkfirst=True)


def migrate(engine: Engine, *, apply: bool = False) -> MigrationReport:
    """Run a real dry-run or explicitly create the additive table."""

    before = preflight(engine)
    if not apply:
        return before
    if not before.safe_to_apply:
        problems = []
        if before.missing_required_tables:
            problems.append(
                "faltan tablas requeridas: "
                + ", ".join(before.missing_required_tables)
            )
        if before.incompatible_tables:
            problems.append(
                "hay tablas Phase 3 incompatibles: "
                + ", ".join(before.incompatible_tables)
            )
        raise PreflightError("; ".join(problems))

    ensure_phase3_tables(engine)
    after_names, _, after_incompatible = _schema_snapshot(engine)
    if after_incompatible:
        raise PreflightError(
            "La tabla creada no coincide con el contrato Phase 3: "
            + ", ".join(sorted(after_incompatible))
        )
    phase3_names = {table.name for table in PHASE3_TABLES}
    after = tuple(sorted(phase3_names & after_names))
    created = tuple(sorted(set(after) - set(before.phase3_tables_before)))
    return MigrationReport(
        applied=True,
        safe_to_apply=True,
        required_tables=before.required_tables,
        missing_required_tables=(),
        phase3_tables_before=before.phase3_tables_before,
        tables_to_create=before.tables_to_create,
        incompatible_tables=(),
        phase3_tables_after=after,
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
        help="Crea exclusivamente la tabla aditiva de políticas de simulacro.",
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
