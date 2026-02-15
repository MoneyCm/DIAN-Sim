import bcrypt
import os
import streamlit as st
from sqlalchemy.orm import Session
# Importación preventiva para registrar todos los modelos en SQLAlchemy registry Mikey
from db.models import User, UserOPEC, Attempt, UserStats, Achievement, Skill, QuestionPerformance
from db.session import SessionLocal

class AuthManager:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), hashed_password.encode())
        except:
            # Fallback for legacy SHA256 if needed during migration
            import hashlib
            legacy = hashlib.sha256(password.encode()).hexdigest()
            return legacy == hashed_password

    @staticmethod
    def login(username, password):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user and AuthManager.verify_password(password, user.password_hash):
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user.id
                st.session_state["username"] = user.username
                st.session_state["user_role"] = user.role
                return True
        except Exception as e:
            print(f"🔥 Auth Error: {e}")
            raise e
        finally:
            db.close()
        return False

    @staticmethod
    def login_with_google(email: str, username: str = None):
        """Autenticar o registrar un usuario usando su cuenta de Google. mikey."""
        db = SessionLocal()
        try:
            # Buscar por email (vínculo principal)
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                # Si no existe, crear uno nuevo con un nombre de usuario basado en el email
                base_username = username if username else email.split('@')[0]
                temp_username = base_username
                counter = 1
                while db.query(User).filter(User.username == temp_username).first():
                    temp_username = f"{base_username}_{counter}"
                    counter += 1
                
                user = User(
                    username=temp_username,
                    email=email,
                    password_hash="GOOGLE_OAUTH" # Marca para saber que no usa pass local
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            # Iniciar sesión en Streamlit
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = user.id
            st.session_state["username"] = user.username
            st.session_state["user_role"] = user.role
            return True
        except Exception as e:
            print(f"🔥 Google Auth Error: {e}")
            return False
        finally:
            db.close()

    @staticmethod
    def logout():
        st.session_state["logged_in"] = False
        st.session_state["user_id"] = None
        st.session_state["username"] = None
        st.session_state["user_role"] = None
        st.rerun()

    @staticmethod
    def check_auth():
        if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
            return False
        return True
