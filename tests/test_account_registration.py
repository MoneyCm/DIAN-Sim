from sqlalchemy import create_engine, text

from core.account_registration import UsernameAlreadyExists, create_password_account


def test_create_password_account_sets_required_free_subscription_tier():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, "
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
            "id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, "
            "role TEXT NOT NULL, subscription_tier TEXT NOT NULL)"
        ))
    create_password_account(engine, "marisol", "hash")

    try:
        create_password_account(engine, "marisol", "other-hash")
    except UsernameAlreadyExists:
        pass
    else:
        raise AssertionError("Expected a duplicate-username error")
