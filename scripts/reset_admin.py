
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import SessionLocal
from db.models import User
from core.auth import AuthManager

def reset_admin_password():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if user:
            print(f"Found user: {user.username}")
            new_password = "admin123"
            hashed = AuthManager.hash_password(new_password)
            user.password_hash = hashed
            db.commit()
            print(f"Password for 'admin' reset to '{new_password}'")
        else:
            print("User 'admin' not found!")
    except Exception as e:
        print(f"Error resetting password: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()
