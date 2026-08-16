from sqlalchemy import create_engine, text

from core.account_registration import (
    GOOGLE_ACCOUNT_INSERT_SQL,
    PASSWORD_ACCOUNT_INSERT_SQL,
    UsernameAlreadyExists,
    create_google_account,
    create_google_account_in_transaction,
    create_password_account,
)
from db.models import User


def _engine_with_current_user_schema():
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    return engine


def test_create_password_account_sets_required_free_subscription_tier():
    engine = _engine_with_current_user_schema()

    create_password_account(engine, "marisol", "hash")

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT username, role, subscription_tier, created_at "
            "FROM users WHERE username = 'marisol'"
        )).one()
    assert tuple(row[:3]) == ("marisol", "user", "free")
    assert row.created_at is not None


def test_create_password_account_rejects_duplicate_username():
    engine = _engine_with_current_user_schema()
    create_password_account(engine, "marisol", "hash")

    try:
        create_password_account(engine, "marisol", "other-hash")
    except UsernameAlreadyExists:
        pass
    else:
        raise AssertionError("Expected a duplicate-username error")


def test_create_google_account_sets_required_free_subscription_tier():
    engine = _engine_with_current_user_schema()

    user_id = create_google_account(engine, "marisol", "marisol@example.com")

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT username, email, password_hash, role, subscription_tier, created_at "
            "FROM users WHERE id = :id"
        ), {"id": user_id}).one()
    assert tuple(row[:5]) == (
        "marisol",
        "marisol@example.com",
        "GOOGLE_OAUTH",
        "user",
        "free",
    )
    assert row.created_at is not None


def test_google_account_can_be_created_in_the_callers_transaction():
    engine = _engine_with_current_user_schema()
    with engine.begin() as conn:
        user_id = create_google_account_in_transaction(conn, "marisol", "marisol@example.com")
        assert user_id == 1


def test_raw_registration_statements_use_portable_current_timestamp():
    for statement in (PASSWORD_ACCOUNT_INSERT_SQL, GOOGLE_ACCOUNT_INSERT_SQL):
        normalized = " ".join(statement.upper().split())
        assert "CREATED_AT" in normalized
        assert "CURRENT_TIMESTAMP" in normalized
        assert "NOW()" not in normalized
