
import os
from cryptography.fernet import Fernet

# Key path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.join(BASE_DIR, "secret.key")


class EncryptionKeyConfigurationError(RuntimeError):
    """Raised when a managed environment has no stable encryption key."""


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _requires_configured_key() -> bool:
    environment = os.getenv("DIAN_SIM_ENV", "development").strip().lower()
    return environment in {"production", "prod", "cloud"} or _is_truthy(
        os.getenv("REQUIRE_DATABASE_URL")
    )

def load_or_generate_key():
    """Carga una llave persistente; el archivo es sólo el respaldo local."""
    configured_key = os.getenv("DIAN_SIM_FERNET_KEY", "").strip()
    if not configured_key:
        try:
            import streamlit as st
            configured_key = st.secrets.get("DIAN_SIM_FERNET_KEY", "").strip()
        except Exception:
            configured_key = ""

    if configured_key:
        key = configured_key.encode("utf-8")
        try:
            Fernet(key)
        except (TypeError, ValueError) as exc:
            raise EncryptionKeyConfigurationError(
                "DIAN_SIM_FERNET_KEY no contiene una clave Fernet válida."
            ) from exc
        return key

    if _requires_configured_key():
        raise EncryptionKeyConfigurationError(
            "DIAN_SIM_FERNET_KEY es obligatoria en producción y debe permanecer "
            "estable entre despliegues."
        )

    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as key_file:
            return key_file.read()

    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
    return key

_cipher_suite = None

def get_cipher():
    global _cipher_suite
    if _cipher_suite is None:
        key = load_or_generate_key()
        _cipher_suite = Fernet(key)
    return _cipher_suite

def encrypt_value(raw_text: str) -> str:
    """Encripta un string usando Fernet."""
    if not raw_text: 
        return ""
    cipher = get_cipher()
    # Fernet expects bytes
    encrypted_bytes = cipher.encrypt(raw_text.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_value(encrypted_text: str) -> str:
    """Desencripta un string encriptado."""
    if not encrypted_text:
        return ""
    try:
        cipher = get_cipher()
        decoded_bytes = cipher.decrypt(encrypted_text.encode("utf-8"))
        return decoded_bytes.decode("utf-8")
    except EncryptionKeyConfigurationError:
        raise
    except Exception as e:
        print(f"Error descifrando llave: {type(e).__name__}")
        return ""
