from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.simulation_policy import SimulationPolicyValidationError
from core.simulation_policy_store import (
    SimulationPolicyStoreError,
    create_initial_simulation_policy,
    create_simulation_policy_version,
    load_active_simulation_policy,
)
from db.models import Base, Competition, OpecProfile, OpecSimulationPolicy


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    competition = Competition(name="DIAN 2676", code="DIAN-2676")
    session.add(competition)
    session.flush()
    session.add(OpecProfile(
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=[{"number": value} for value in range(1, 10)],
    ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_initial_policy_uses_function_count_and_keeps_official_unknown(db):
    row = create_initial_simulation_policy(
        db,
        competition_id=1,
        opec_number="236769",
        actor="admin@example.com",
    )
    db.commit()

    assert row.internal_diagnostic_questions == 9
    assert row.internal_full_questions == 60
    assert row.official_question_count is None
    assert row.official_duration_minutes is None

    _, active, resolved = load_active_simulation_policy(
        db, competition_id=1, opec_number="236769"
    )
    assert active.id == row.id
    assert resolved.policy_version == "opec-236769-simulation-v1"


def test_version_change_preserves_history_and_one_active_row(db):
    first = create_initial_simulation_policy(
        db, competition_id=1, opec_number="236769", actor="admin"
    )
    db.commit()

    second = create_simulation_policy_version(
        db,
        current=first,
        updates={
            "internal_full_questions": 45,
            "internal_minutes_per_question": 1.5,
            "policy_status": "provisional",
        },
        actor="admin",
        change_reason="Ajuste experimental del plan interno.",
    )
    db.commit()

    assert second.version_number == 2
    assert second.supersedes_policy_id == first.id
    assert second.internal_full_questions == 45
    rows = db.query(OpecSimulationPolicy).order_by(
        OpecSimulationPolicy.version_number
    ).all()
    assert [(row.version_number, row.is_active, row.active_slot) for row in rows] == [
        (1, False, None),
        (2, True, 1),
    ]


def test_official_partial_requires_https_source_and_version(db):
    with pytest.raises(SimulationPolicyValidationError):
        create_initial_simulation_policy(
            db,
            competition_id=1,
            opec_number="236769",
            actor="admin",
            official_partial={
                "official_max_questions_per_case": 3,
                "official_source_status": "partial",
            },
        )


def test_known_official_partial_does_not_invent_count_or_duration(db):
    row = create_initial_simulation_policy(
        db,
        competition_id=1,
        opec_number="236769",
        actor="admin",
        official_partial={
            "official_max_questions_per_case": 3,
            "official_source_title": "CNSC LP-004-2026",
            "official_source_url": (
                "https://community.secop.gov.co/Public/Archive/RetrieveFile/Index"
                "?DocumentId=783745811&InCommunity=False&InPaymentGateway=False"
            ),
            "official_source_version": "LP-004-2026 consultado 2026-08-15",
            "official_source_status": "partial",
            "official_verified_at": datetime(2026, 8, 15),
        },
    )

    assert row.official_max_questions_per_case == 3
    assert row.official_question_count is None
    assert row.official_duration_minutes is None


def test_initial_creation_is_not_silently_repeated(db):
    create_initial_simulation_policy(
        db, competition_id=1, opec_number="236769", actor="admin"
    )
    db.commit()

    with pytest.raises(SimulationPolicyStoreError, match="historial"):
        create_initial_simulation_policy(
            db, competition_id=1, opec_number="236769", actor="admin"
        )
