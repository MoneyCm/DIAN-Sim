import pytest

import db.session as db_session


def test_required_database_url_never_falls_back_to_sqlite(monkeypatch):
    monkeypatch.setenv("DIAN_SIM_ENV", "production")
    monkeypatch.setenv("REQUIRE_DATABASE_URL", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db_session, "_streamlit_database_url", lambda: None)

    with pytest.raises(db_session.MissingDatabaseURLError):
        db_session._resolve_database_url(testing=False)


def test_secret_lookup_failure_is_propagated_when_remote_db_is_required(monkeypatch):
    monkeypatch.setenv("DIAN_SIM_ENV", "cloud")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def fail_secret_lookup():
        raise FileNotFoundError("secrets unavailable")

    monkeypatch.setattr(db_session, "_streamlit_database_url", fail_secret_lookup)

    with pytest.raises(db_session.MissingDatabaseURLError):
        db_session._resolve_database_url(testing=False)


def test_local_development_keeps_the_sqlite_fallback(monkeypatch):
    monkeypatch.setenv("DIAN_SIM_ENV", "development")
    monkeypatch.delenv("REQUIRE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db_session, "_streamlit_database_url", lambda: None)

    assert db_session._resolve_database_url(testing=False).startswith("sqlite:///")
