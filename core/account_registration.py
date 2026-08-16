"""Safe creation of password-based study accounts."""

from sqlalchemy import text


class UsernameAlreadyExists(ValueError):
    """Raised when an account name is already in use."""


GOOGLE_ACCOUNT_INSERT_SQL = (
    "INSERT INTO users "
    "(username, email, password_hash, role, subscription_tier, created_at) "
    "VALUES "
    "(:username, :email, 'GOOGLE_OAUTH', 'user', 'free', CURRENT_TIMESTAMP) "
    "RETURNING id"
)

PASSWORD_ACCOUNT_INSERT_SQL = (
    "INSERT INTO users "
    "(username, password_hash, role, subscription_tier, created_at) "
    "VALUES (:username, :password_hash, 'user', 'free', CURRENT_TIMESTAMP)"
)


def create_password_account(engine, username: str, password_hash: str) -> None:
    """Create a free account, including fields required by legacy schemas."""
    with engine.connect() as check_conn:
        existing = check_conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).first()
    if existing:
        raise UsernameAlreadyExists(username)

    with engine.begin() as insert_conn:
        insert_conn.execute(
            text(PASSWORD_ACCOUNT_INSERT_SQL),
            {"username": username, "password_hash": password_hash},
        )


def create_google_account(engine, username: str, email: str) -> int:
    """Create the local account that backs a verified Google sign-in."""
    with engine.begin() as insert_conn:
        return create_google_account_in_transaction(insert_conn, username, email)


def create_google_account_in_transaction(connection, username: str, email: str) -> int:
    """Create a Google account using the caller's active transaction.

    Keeping lookup, insertion and onboarding checks on one connection prevents
    a callback request from holding one pooled database connection while it
    waits for a second one to insert the account.
    """
    return connection.execute(
        text(GOOGLE_ACCOUNT_INSERT_SQL),
        {"username": username, "email": email},
    ).scalar_one()
