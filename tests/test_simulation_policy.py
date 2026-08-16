from datetime import datetime

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from core.simulation_policy import (
    SimulationPolicyValidationError,
    next_policy_version,
    provisional_policy_values,
    resolve_active_policy,
    resolve_simulation_policy,
    validate_policy_scope,
    validate_policy_values,
)
from db.models import Base, Competition, OpecProfile, OpecSimulationPolicy
from scripts.migrations.phase3_simulation_policy import (
    PHASE3_TABLES,
    PreflightError,
    migrate,
)


NOW = datetime(2026, 8, 15, 12, 0)


def _engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _foreign_keys_on(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _database():
    engine = _engine()
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    competition = Competition(code="POLICY", name="Concurso de política")
    db.add(competition)
    db.flush()
    profile = OpecProfile(
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        source_status="verified_current",
    )
    db.add(profile)
    db.commit()
    return engine, db, competition, profile


def _policy(db, competition, profile, **overrides):
    values = provisional_policy_values(profile.opec_number)
    values.update({
        "competition_id": competition.id,
        "opec_profile_id": profile.id,
    })
    values.update(overrides)
    row = OpecSimulationPolicy(**values)
    db.add(row)
    db.commit()
    return row


def test_defaults_are_explicitly_provisional_and_official_fields_stay_null():
    _engine_row, db, competition, profile = _database()
    row = _policy(db, competition, profile)

    assert row.policy_status == "provisional"
    assert row.internal_diagnostic_questions == 9
    assert row.internal_short_questions == 15
    assert row.internal_partial_questions == 30
    assert row.internal_full_questions == 60
    assert row.internal_minutes_per_question == 2.0
    assert row.internal_max_questions_per_case == 3
    assert row.internal_navigation_mode == "sequential"
    assert row.official_question_count is None
    assert row.official_duration_minutes is None
    assert row.official_composition_json is None
    assert row.official_source_url is None

    resolved = resolve_simulation_policy(row, opec_number="236769")
    assert resolved.is_provisional is True
    assert resolved.internal.mode("diagnostic").duration_minutes == 18
    assert resolved.internal.mode("full").duration_minutes == 120
    assert resolved.official.has_published_parameters is False


def test_verified_official_parameters_remain_separate_from_internal_modes():
    values = provisional_policy_values("236769")
    values.update({
        "policy_status": "verified",
        "official_question_count": 80,
        "official_duration_minutes": 180,
        "official_max_questions_per_case": 3,
        "official_navigation_mode": "free",
        "official_composition_json": {"functional": 70, "behavioral": 30},
        "official_weights_json": {"functional": 70, "behavioral": 30},
        "official_source_title": "Guía oficial",
        "official_source_url": "https://www.cnsc.gov.co/guia.pdf",
        "official_source_version": "GOA-2026-1",
        "official_source_status": "verified_current",
        "official_verified_at": NOW,
    })

    resolved = resolve_simulation_policy(values, opec_number="236769")

    assert resolved.internal.mode("full").question_count == 60
    assert resolved.official.question_count == 80
    assert resolved.official.duration_minutes == 180
    assert resolved.official.composition == {"functional": 0.7, "behavioral": 0.3}
    assert resolved.is_provisional is False


def test_provisional_diagnostic_size_can_follow_opec_function_count():
    nine = resolve_simulation_policy(
        None,
        opec_number="236769",
        function_count=9,
    )
    sixteen = resolve_simulation_policy(
        None,
        opec_number="252097",
        function_count=16,
    )

    assert nine.internal.mode("diagnostic").question_count == 9
    assert nine.internal.mode("short").question_count == 15
    assert sixteen.internal.mode("diagnostic").question_count == 16
    assert sixteen.internal.mode("short").question_count == 16
    assert sixteen.internal.mode("partial").question_count == 30
    assert sixteen.official.question_count is None


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"internal_diagnostic_questions": 30}, "diagnóstico <= corto"),
        ({"internal_minutes_per_question": 0}, "mayor que 0"),
        ({"internal_max_questions_per_case": 11}, "entre 1 y 10"),
        ({"internal_navigation_mode": "random"}, "Navegación interna"),
        ({"internal_weights_json": {"functional": 0.8}}, "sumar 1.0"),
        ({"internal_minutes_per_question": float("nan")}, "mayor que 0"),
        ({"internal_full_questions": True}, "entero positivo"),
        ({"is_active": 1}, "debe ser booleano"),
        ({"internal_composition_json": [1.0]}, "objeto JSON"),
        (
            {"internal_weights_json": {"behavioral": 1.0}},
            "mismas categorías",
        ),
        ({"official_question_count": 80}, "URL, versión y estado"),
        ({"policy_status": "retired", "is_active": True}, "retirada"),
    ],
)
def test_pure_validation_rejects_ambiguous_or_invalid_configuration(updates, message):
    values = provisional_policy_values("236769")
    values.update(updates)

    with pytest.raises(SimulationPolicyValidationError, match=message):
        validate_policy_values(values)


def test_official_unpublished_status_cannot_carry_exam_parameters():
    values = provisional_policy_values("236769")
    values.update({
        "official_question_count": 60,
        "official_source_url": "https://www.cnsc.gov.co/proceso",
        "official_source_version": "consulta-2026-08-15",
        "official_source_status": "unpublished",
    })

    with pytest.raises(SimulationPolicyValidationError, match="no publicada"):
        validate_policy_values(values)


def test_partial_official_evidence_can_establish_only_maximum_per_case():
    values = provisional_policy_values("236769")
    values.update({
        "official_max_questions_per_case": 3,
        "official_source_url": "https://www.cnsc.gov.co/especificacion-tecnica.pdf",
        "official_source_version": "LP-004-2026",
        "official_source_status": "partial",
        "official_verified_at": NOW,
    })

    resolved = resolve_simulation_policy(values, opec_number="236769")

    assert resolved.official.max_questions_per_case == 3
    assert resolved.official.question_count is None
    assert resolved.official.duration_minutes is None
    assert resolved.policy_status == "provisional"


def test_next_version_is_additive_and_does_not_mutate_current_record():
    _engine_row, db, competition, profile = _database()
    current = _policy(db, competition, profile)

    values = next_policy_version(current, {
        "internal_short_questions": 25,
        "internal_partial_questions": 45,
        "internal_full_questions": 70,
        "change_reason": "Ajuste editorial de carga.",
        "actor": "admin@example.com",
    })

    assert current.version_number == 1
    assert current.internal_short_questions == 15
    assert values["version_number"] == 2
    assert values["policy_version"] == "opec-236769-simulation-v2"
    assert values["supersedes_policy_id"] == current.id
    assert values["policy_status"] == "draft"
    assert values["active_slot"] == 1
    assert values["internal_short_questions"] == 25
    assert values["competition_id"] == competition.id
    assert values["opec_profile_id"] == profile.id


def test_active_resolution_is_opec_scoped_and_rejects_two_active_versions():
    first = provisional_policy_values("236769")
    second = provisional_policy_values("242699")
    selected = resolve_active_policy([first, second], opec_number="236769")
    assert selected.opec_number == "236769"

    duplicate = dict(first)
    duplicate["version_number"] = 2
    duplicate["policy_version"] = "opec-236769-simulation-v2"
    with pytest.raises(SimulationPolicyValidationError, match="más de una"):
        resolve_active_policy([first, duplicate], opec_number="236769")


def test_database_constraints_versioning_counts_and_verified_source():
    _engine_row, db, competition, profile = _database()
    _policy(db, competition, profile)

    with pytest.raises(IntegrityError):
        _policy(db, competition, profile, policy_version="duplicate-label")
    db.rollback()

    invalid_counts = provisional_policy_values("236769", version_number=2)
    invalid_counts.update({
        "competition_id": competition.id,
        "opec_profile_id": profile.id,
        "internal_diagnostic_questions": 30,
        "internal_short_questions": 20,
        "is_active": False,
        "active_slot": None,
    })
    db.add(OpecSimulationPolicy(**invalid_counts))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    unsupported_official = provisional_policy_values("236769", version_number=4)
    unsupported_official.update({
        "competition_id": competition.id,
        "opec_profile_id": profile.id,
        "official_question_count": 80,
        "is_active": False,
        "active_slot": None,
    })
    db.add(OpecSimulationPolicy(**unsupported_official))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    invalid_verified = provisional_policy_values("236769", version_number=3)
    invalid_verified.update({
        "competition_id": competition.id,
        "opec_profile_id": profile.id,
        "policy_status": "verified",
        "is_active": False,
        "active_slot": None,
    })
    db.add(OpecSimulationPolicy(**invalid_verified))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_guarantees_one_active_version_per_opec_profile():
    _engine_row, db, competition, profile = _database()
    first = _policy(db, competition, profile)
    second_values = provisional_policy_values("236769", version_number=2)
    second_values.update({
        "competition_id": competition.id,
        "opec_profile_id": profile.id,
    })
    db.add(OpecSimulationPolicy(**second_values))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    first.is_active = False
    first.active_slot = None
    db.commit()
    db.add(OpecSimulationPolicy(**second_values))
    db.commit()
    assert db.query(OpecSimulationPolicy).filter_by(is_active=True).count() == 1


def test_scope_validator_rejects_profile_or_competition_mismatch():
    _engine_row, db, competition, profile = _database()
    row = _policy(db, competition, profile)
    assert validate_policy_scope(row, profile)["opec_profile_id"] == profile.id

    wrong = dict(validate_policy_values(row))
    wrong["competition_id"] = competition.id + 100
    with pytest.raises(SimulationPolicyValidationError, match="perfil OPEC"):
        validate_policy_scope(wrong, profile)


def test_phase3_migration_is_dry_run_then_idempotent_without_legacy_changes():
    engine = _engine()
    Base.metadata.create_all(
        engine,
        tables=[Competition.__table__, OpecProfile.__table__],
    )
    with engine.connect() as connection:
        inspector = inspect(connection)
        competition_columns = {
            column["name"] for column in inspector.get_columns("competitions")
        }
        profile_columns = {
            column["name"] for column in inspector.get_columns("opec_profiles")
        }

    dry_run = migrate(engine)
    assert dry_run.applied is False
    assert dry_run.safe_to_apply is True
    assert dry_run.tables_to_create == ("opec_simulation_policies",)
    assert "opec_simulation_policies" not in inspect(engine).get_table_names()

    first = migrate(engine, apply=True)
    second = migrate(engine, apply=True)

    assert first.tables_created == ("opec_simulation_policies",)
    assert second.tables_created == ()
    assert second.phase3_tables_after == tuple(table.name for table in PHASE3_TABLES)
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert competition_columns == {
            column["name"] for column in inspector.get_columns("competitions")
        }
        assert profile_columns == {
            column["name"] for column in inspector.get_columns("opec_profiles")
        }


def test_phase3_migration_refuses_missing_dependencies_and_incompatible_table():
    missing = _engine()
    with pytest.raises(PreflightError, match="faltan tablas"):
        migrate(missing, apply=True)

    incompatible = _engine()
    Base.metadata.create_all(
        incompatible,
        tables=[Competition.__table__, OpecProfile.__table__],
    )
    with incompatible.begin() as connection:
        connection.execute(text(
            "CREATE TABLE opec_simulation_policies (id VARCHAR(36) PRIMARY KEY)"
        ))
    report = migrate(incompatible)
    assert report.safe_to_apply is False
    assert report.incompatible_tables == ("opec_simulation_policies",)
    with pytest.raises(PreflightError, match="incompatibles"):
        migrate(incompatible, apply=True)


def test_phase3_table_compiles_for_sqlite_and_postgresql():
    table = OpecSimulationPolicy.__table__
    sqlite_ddl = str(CreateTable(table).compile(dialect=_engine().dialect))
    postgres_ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))

    assert "opec_simulation_policies" in sqlite_ddl
    assert "opec_simulation_policies" in postgres_ddl
    assert "JSON" in sqlite_ddl
    assert "JSON" in postgres_ddl
