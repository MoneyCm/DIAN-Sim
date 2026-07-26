from pathlib import Path

from app.ui_utils import escape_html
from core.auth import AuthManager


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class _Connection:
    def __init__(self, role):
        self.role = role

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _statement, params):
        assert params == {"uid": 7}
        return _Result(self.role)


class _Engine:
    def __init__(self, role):
        self.role = role

    def connect(self):
        return _Connection(self.role)


def test_escape_html_blocks_markup():
    assert escape_html('<script>alert("x")</script>') == (
        "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
    )


def test_admin_authorization_uses_database_role(monkeypatch):
    import core.auth as auth_module
    import db.session as session_module

    session_state = {"logged_in": True, "user_id": 7, "username": "cesar"}
    monkeypatch.setattr(auth_module.st, "session_state", session_state)
    monkeypatch.setattr(session_module, "engine", _Engine("user"))

    assert AuthManager.is_admin() is False
    assert session_state["user_role"] == "user"

    monkeypatch.setattr(session_module, "engine", _Engine("admin"))
    assert AuthManager.is_admin() is True


def test_oauth_has_no_legacy_username_linking():
    source = Path("core/auth.py").read_text(encoding="utf-8")
    assert "sql_legacy" not in source
    assert 'username\") != "cesar"' not in source