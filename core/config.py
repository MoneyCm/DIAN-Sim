import os
from dotenv import load_dotenv, set_key
import streamlit as st
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import Configuration

# Build absolute paths relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Pre-load existing env
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

def get_api_key(provider: str) -> str:
    """
    Obtiene la API Key con prioridad:
    1. Streamlit Secrets (Cloud)
    2. Base de Datos Central (Sincronizada PC/Móvil)
    3. Entorno / .env Local
    """
    key_name = f"{provider.upper()}_API_KEY"
    
    # 1. Try Secrets first (for Streamlit Cloud hardcoded config)
    try:
        secret_val = st.secrets.get(key_name)
        if secret_val:
            return secret_val
    except:
        pass

    # 2. Try DB (Centralized Config)
    db = SessionLocal()
    try:
        config_entry = db.query(Configuration).filter_by(key_name=key_name).first()
        if config_entry:
            return config_entry.value
    except Exception as e:
        print(f"DB Config error: {e}")
    finally:
        db.close()
        
    # 3. Fallback to os.environ (Local .env)
    return os.getenv(key_name, "")

def save_api_key_persistent(provider: str, value: str) -> bool:
    """
    Guarda la API Key en la BASE DE DATOS (Multi-dispositivo) 
    y opcionalmente en el .env local si existe acceso.
    """
    key_name = f"{provider.upper()}_API_KEY"
    success = False
    
    # 1. Save to DB (Priority)
    db = SessionLocal()
    try:
        clean_val = value.strip() # Clean white spaces
        config_entry = db.query(Configuration).filter_by(key_name=key_name).first()
        if config_entry:
            config_entry.value = clean_val
        else:
            config_entry = Configuration(key_name=key_name, value=clean_val)
            db.add(config_entry)
        db.commit()
        print(f"✅ API Key for {provider} saved to central DB.")
        success = True
    except Exception as e:
        print(f"❌ Error saving API Key to DB: {e}")
        db.rollback()
    finally:
        db.close()

    # 2. Save to .env (Local Backup/Convenience)
    try:
        if not os.path.exists(ENV_PATH):
            with open(ENV_PATH, "w") as f:
                f.write("# DIAN Sim - Environment Configuration\n")
        set_key(ENV_PATH, key_name, clean_val)
        os.environ[key_name] = clean_val
        print(f"✅ API Key for {provider} saved to local .env.")
    except Exception as e:
        print(f"⚠️ Notice: Could not save to local .env (Cloud env?): {e}")
        
    return success

# Alias for compatibility if needed
def save_api_key_local(provider: str, value: str) -> bool:
    return save_api_key_persistent(provider, value)
