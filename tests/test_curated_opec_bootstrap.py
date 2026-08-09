from core.curated_opec_bootstrap import BOOTSTRAP_ENV, OPEC_241130_BOOTSTRAP_ENV, is_enabled


def test_bootstrap_requires_explicit_environment_flag(monkeypatch):
    monkeypatch.delenv(BOOTSTRAP_ENV, raising=False)
    assert not is_enabled()
    monkeypatch.setenv(BOOTSTRAP_ENV, "true")
    assert is_enabled()


def test_each_curated_bank_requires_its_own_flag(monkeypatch):
    monkeypatch.delenv(OPEC_241130_BOOTSTRAP_ENV, raising=False)
    assert not is_enabled(OPEC_241130_BOOTSTRAP_ENV)
    monkeypatch.setenv(OPEC_241130_BOOTSTRAP_ENV, "yes")
    assert is_enabled(OPEC_241130_BOOTSTRAP_ENV)
