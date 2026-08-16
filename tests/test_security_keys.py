from cryptography.fernet import Fernet
import pytest

import core.security_keys as security_keys


class _StreamlitWithoutSecrets:
    secrets = {}


def _reset_cipher(monkeypatch, tmp_path):
    monkeypatch.setattr(security_keys, "_cipher_suite", None)
    monkeypatch.setattr(security_keys, "KEY_FILE", str(tmp_path / "secret.key"))
    monkeypatch.setitem(__import__("sys").modules, "streamlit", _StreamlitWithoutSecrets())
    monkeypatch.delenv("DIAN_SIM_FERNET_KEY", raising=False)
    monkeypatch.delenv("REQUIRE_DATABASE_URL", raising=False)


def test_local_development_generates_and_reuses_a_cipher(monkeypatch, tmp_path):
    _reset_cipher(monkeypatch, tmp_path)
    monkeypatch.setenv("DIAN_SIM_ENV", "development")

    encrypted = security_keys.encrypt_value("clave-local")

    assert encrypted != "clave-local"
    assert security_keys.decrypt_value(encrypted) == "clave-local"
    assert (tmp_path / "secret.key").exists()


def test_production_requires_an_explicit_stable_fernet_key(monkeypatch, tmp_path):
    _reset_cipher(monkeypatch, tmp_path)
    monkeypatch.setenv("DIAN_SIM_ENV", "production")
    (tmp_path / "secret.key").write_bytes(Fernet.generate_key())

    with pytest.raises(security_keys.EncryptionKeyConfigurationError):
        security_keys.get_cipher()


def test_production_accepts_a_valid_configured_key(monkeypatch, tmp_path):
    _reset_cipher(monkeypatch, tmp_path)
    monkeypatch.setenv("DIAN_SIM_ENV", "cloud")
    monkeypatch.setenv("DIAN_SIM_FERNET_KEY", Fernet.generate_key().decode("utf-8"))

    encrypted = security_keys.encrypt_value("clave-remota")

    assert security_keys.decrypt_value(encrypted) == "clave-remota"
    assert not (tmp_path / "secret.key").exists()
