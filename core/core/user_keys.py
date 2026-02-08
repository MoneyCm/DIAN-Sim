
from sqlalchemy.orm import Session
from db.models import UserAPIKey
from db.session import SessionLocal
from core.security_keys import encrypt_value, decrypt_value

def save_user_key(user_id: int, provider: str, raw_key: str) -> bool:
    """Guarda (encriptada) la API key de un usuario específico."""
    if not user_id or not raw_key:
        return False
        
    db: Session = SessionLocal()
    try:
        provider = provider.lower()
        # Check if key exists
        existing = db.query(UserAPIKey).filter_by(user_id=user_id, provider=provider).first()
        
        encrypted = encrypt_value(raw_text=raw_key)
        
        if existing:
            existing.encrypted_key = encrypted
        else:
            new_key = UserAPIKey(user_id=user_id, provider=provider, encrypted_key=encrypted)
            db.add(new_key)
            
        db.commit()
        return True
    except Exception as e:
        print(f"Error guardando llave usuario {user_id}: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_user_key(user_id: int, provider: str) -> str:
    """Recupera (desencriptada) la API key de un usuario."""
    if not user_id:
        return None
        
    db: Session = SessionLocal()
    try:
        provider = provider.lower()
        entry = db.query(UserAPIKey).filter_by(user_id=user_id, provider=provider).first()
        
        if entry:
            return decrypt_value(entry.encrypted_key)
        return None
    except Exception as e:
        print(f"Error recuperando llave usuario {user_id}: {e}")
        return None
    finally:
        db.close()
