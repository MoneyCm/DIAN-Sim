from core.curated_opec_bootstrap import BOOTSTRAP_ENV, is_enabled


def test_bootstrap_requires_explicit_environment_flag(monkeypatch):
    monkeypatch.delenv(BOOTSTRAP_ENV, raising=False)
    assert not is_enabled()
    monkeypatch.setenv(BOOTSTRAP_ENV, "true")
    assert is_enabled()
