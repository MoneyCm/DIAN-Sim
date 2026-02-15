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
        # 1. Login Manual (session_state)
        manual_login = "logged_in" in st.session_state and st.session_state["logged_in"]
        
        # 2. Login Nativo (Streamlit OIDC) mikey v3.0
        native_user = getattr(st, "user", None)
        native_login = native_user.is_logged_in if native_user else False
        
        if native_login and not manual_login:
            # Sincronizar login nativo con sesión local mikey
            AuthManager.login_with_google(st.user.email, st.user.name)
            return True
        return manual_login

    @staticmethod
    def is_pro():
        """Verifica si el usuario actual es PRO mikey v4.0"""
        if "user_id" not in st.session_state:
            return False
        
        # Admin es siempre PRO
        if st.session_state.get("user_role") == "admin":
            return True
            
        from db.session import SessionLocal
        from db.models import User
        from datetime import datetime
        
        try:
            with SessionLocal() as db:
                user = db.query(User).filter_by(id=st.session_state["user_id"]).first()
                if not user:
                    return False
                
                # Verificar suscripción Pro activa (v4.0 columns) mikey
                if hasattr(user, "subscription_tier") and user.subscription_tier == "pro":
                    if user.subscription_expiry:
                        return user.subscription_expiry > datetime.now()
                    return True # Pro vitalicio
        except Exception as e:
            # Si hay un error (ej: columna no existe aún), devolvemos False (Free)
            print(f"⚠️ [AUTH] is_pro error (likely migration in progress): {e}")
            return False
                
        return False
