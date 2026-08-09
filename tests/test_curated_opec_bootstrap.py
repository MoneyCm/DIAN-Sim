from core import curated_opec_bootstrap
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


def test_completed_banks_do_not_run_seeders_on_every_rerun(monkeypatch):
    monkeypatch.setenv(BOOTSTRAP_ENV, "true")
    monkeypatch.setattr(curated_opec_bootstrap, "_bank_is_ready", lambda *_args, **_kwargs: True)

    assert curated_opec_bootstrap.run_if_enabled() == {}
