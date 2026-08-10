from pathlib import Path


def test_google_account_creation_reloads_current_registration_helper():
    source = Path("core/auth.py").read_text(encoding="utf-8")
    assert 'AUTH_RUNTIME_VERSION = "google-free-tier-v3"' in source
    assert "account_registration = importlib.reload(account_registration)" in source
    assert "google_login_error" in source
