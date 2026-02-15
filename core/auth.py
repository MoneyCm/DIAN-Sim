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
        from db.session import engine
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                # Mikey v6.0: SQL crudo para evitar fallos por columnas faltantes
                sql = text("SELECT id, username, password_hash, role FROM users WHERE username = :u")
                row = conn.execute(sql, {"u": username}).first()
                
                if row and AuthManager.verify_password(password, row[2]):
                    st.session_state["logged_in"] = True
                    st.session_state["user_id"] = row[0]
                    st.session_state["username"] = row[1]
                    st.session_state["user_role"] = row[3]
                    return True
        except Exception as e:
            print(f"🔥 Auth Error mikey v6.0: {e}")
            return False
        return False

    @staticmethod
    def login_with_google(email: str, username: str = None):
        """Autenticar o registrar un usuario usando su cuenta de Google. mikey v6.0."""
        from db.session import engine
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                # 1. Buscar usuario
                sql_find = text("SELECT id, username, role FROM users WHERE email = :e")
                user_row = conn.execute(sql_find, {"e": email}).first()
                
                if not user_row:
                    # Registro de emergencia con SQL crudo
                    base_username = username if username else email.split('@')[0]
                    # Simplificamos: no comprobamos duplicados de forma compleja aquí para evitar fallos
                    sql_ins = text("INSERT INTO users (username, email, password_hash, role) VALUES (:u, :e, 'GOOGLE_OAUTH', 'user') RETURNING id")
                    with engine.begin() as t_conn:
                        new_id = t_conn.execute(sql_ins, {"u": base_username, "e": email}).scalar()
                        user_id = new_id
                        user_name = base_username
                        user_role = "user"
                else:
                    user_id, user_name, user_role = user_row
                
                # Iniciar sesión en Streamlit
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user_id
                st.session_state["username"] = user_name
                st.session_state["user_role"] = user_role
                return True
        except Exception as e:
            print(f"🔥 Google Auth Error mikey v6.0: {e}")
            return False

    @staticmethod
    def logout():
        st.session_state["logged_in"] = False
        st.session_state["user_id"] = None
        st.session_state["username"] = None
        st.session_state["user_role"] = None
        # Quitamos st.rerun() porque esto se usa como callback y Streamlit ya refresca solo.

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
        if "user_id" not in st.session_state or not st.session_state["user_id"]:
            return False
        
        # Admin es siempre PRO
        if st.session_state.get("user_role") == "admin":
            return True
            
        from db.session import SessionLocal
        from db.models import User
        from datetime import datetime
        
        try:
            from db.session import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                # Mikey v5.0: RAW SQL total para evitar problemas de caché ORM
                sql = text("SELECT subscription_tier, subscription_expiry FROM users WHERE id = :uid")
                row = conn.execute(sql, {"uid": st.session_state["user_id"]}).first()
                if row:
                    tier, expiry = row[0], row[1]
                    if tier == "pro":
                        if expiry:
                            if isinstance(expiry, str):
                                from datetime import datetime
                                expiry = datetime.fromisoformat(expiry)
                            from datetime import datetime
                            return expiry > datetime.now()
                        return True
        except Exception as e:
            # Fallback total: Ante la duda, es usuario FREE (pero no crashea la app)
            print(f"⚠️ [AUTH] is_pro critical fallback: {e}")
            return False
                
        return False
                
        return False
