import time

from core.auth_session import create_session_token, verify_session_token


def test_signed_session_token_round_trip():
    token = create_session_token(7, "cesar", "user", "secret", 3600)
    payload = verify_session_token(token, "secret")
    assert payload["uid"] == 7
    assert payload["username"] == "cesar"


def test_session_token_rejects_tampering_and_wrong_secret():
    token = create_session_token(7, "cesar", "user", "secret", 3600)
    assert verify_session_token(token + "x", "secret") is None
    assert verify_session_token(token, "another-secret") is None


def test_session_token_expires():
    token = create_session_token(7, "cesar", "user", "secret", 1)
    assert verify_session_token(token, "secret", now=int(time.time()) + 2) is None
