import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.ai.usage_policy import (
    AIUsageLimitError,
    AIUsagePolicy,
    assert_ai_usage_allowed,
    reserve_ai_usage,
)
from db.models import AICallLog, Base, User


def _factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _policy(**overrides):
    values = {
        "max_prompt_chars": 100,
        "max_calls_per_job": 3,
        "max_calls_per_user_day": 3,
        "max_calls_global_day": 6,
        "max_input_tokens_per_user_day": 100,
        "max_output_tokens_per_user_day": 50,
        "max_output_tokens_per_call": 20,
    }
    values.update(overrides)
    return AIUsagePolicy(**values)


def _log(db, *, user_id, created_at, input_tokens=1, output_tokens=1):
    db.add(
        AICallLog(
            user_id=user_id,
            provider="gemini",
            model="model",
            task_type="test",
            prompt_version="v1",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=1,
            success=True,
            created_at=created_at,
        )
    )


def test_prompt_and_job_size_are_rejected_before_provider_call():
    with pytest.raises(AIUsageLimitError, match="caracteres"):
        assert_ai_usage_allowed(
            None, user_id=1, prompt="x" * 101, policy=_policy()
        )
    with pytest.raises(AIUsageLimitError, match="lote"):
        assert_ai_usage_allowed(
            None, user_id=1, prompt="ok", planned_calls=4, policy=_policy()
        )


def test_daily_user_call_limit_counts_failed_or_successful_logged_attempts():
    factory = _factory()
    db = factory()
    user = User(username="limited", password_hash="x", role="admin")
    db.add(user)
    db.commit()
    now = dt.datetime(2026, 8, 15, 12, 0, 0)
    for _ in range(2):
        _log(db, user_id=user.id, created_at=now)
    db.commit()

    with pytest.raises(AIUsageLimitError, match="cuota diaria"):
        assert_ai_usage_allowed(
            db,
            user_id=user.id,
            prompt="short",
            planned_calls=2,
            policy=_policy(),
            now=now,
        )
    db.close()

def test_token_budget_is_checked_without_storing_prompt():
    factory = _factory()
    db = factory()
    user = User(username="tokens", password_hash="x", role="admin")
    db.add(user)
    db.commit()
    now = dt.datetime(2026, 8, 15, 12, 0, 0)
    _log(db, user_id=user.id, created_at=now, input_tokens=99)
    db.commit()
    with pytest.raises(AIUsageLimitError, match="presupuesto diario de texto"):
        assert_ai_usage_allowed(
            db,
            user_id=user.id,
            prompt="12345678",
            policy=_policy(max_calls_per_user_day=10),
            now=now,
        )
    db.close()


def test_reservation_records_bounded_metadata_only():
    factory = _factory()
    db = factory()
    user = User(username="audit", password_hash="x", role="admin")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    reservation = reserve_ai_usage(
        factory,
        user_id=user_id,
        provider="gemini",
        model="flash",
        task_type="batch",
        prompt="sensitive legal source",
        planned_calls=2,
        policy=_policy(),
    )
    reservation.finish(success=True, output_text="structured answer")

    db = factory()
    rows = db.query(AICallLog).all()
    assert len(rows) == 2
    assert all(row.user_id == user_id for row in rows)
    assert all(not hasattr(row, "prompt") for row in rows)
    db.close()
