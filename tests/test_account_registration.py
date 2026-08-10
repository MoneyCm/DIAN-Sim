from sqlalchemy import create_engine, text

from core.account_registration import (
    UsernameAlreadyExists,
    create_google_account,
    create_google_account_in_transaction,
    create_password_account,
)


def test_create_password_account_sets_required_free_subscription_tier():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password_hash TEXT, "
            "role TEXT NOT NULL, subscription_tier TEXT NOT NULL)"
        ))

    create_password_account(engine, "marisol", "hash")

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT username, role, subscription_tier FROM users WHERE username = 'marisol'"
        )).one()
    assert tuple(row) == ("marisol", "user", "free")


def test_create_password_account_rejects_duplicate_username():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password_hash TEXT, "
            "role TEXT NOT NULL, subscription_tier TEXT NOT NULL)"
        ))
    create_password_account(engine, "marisol", "hash")

    try:
        create_password_account(engine, "marisol", "other-hash")
    except UsernameAlreadyExists:
        pass
    else:
        raise AssertionError("Expected a duplicate-username error")


def test_create_google_account_sets_required_free_subscription_tier():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password_hash TEXT, "
            "role TEXT NOT NULL, subscription_tier TEXT NOT NULL)"
        ))

    user_id = create_google_account(engine, "marisol", "marisol@example.com")

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT username, email, password_hash, role, subscription_tier FROM users WHERE id = :id"
        ), {"id": user_id}).one()
    assert tuple(row) == ("marisol", "marisol@example.com", "GOOGLE_OAUTH", "user", "free")


def test_google_account_can_be_created_in_the_callers_transaction():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password_hash TEXT, "
            "role TEXT NOT NULL, subscription_tier TEXT NOT NULL)"
        ))
        user_id = create_google_account_in_transaction(conn, "marisol", "marisol@example.com")
        assert user_id == 1
