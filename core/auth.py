import bcrypt
import os
import sys
import streamlit as st
from sqlalchemy import text

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
            import hashlib
            legacy = hashlib.sha256(password.encode()).hexdigest()
            return legacy == hashed_password

    @staticmethod
    def login(username, password):
        from db.session import engine
        try:
            with engine.connect() as conn:
                sql = text("SELECT id, username, password_hash, role FROM users WHERE username = :u")
                row = conn.execute(sql, {"u": username}).first()
                if row and AuthManager.verify_password(password, row[2]):
                    st.session_state["logged_in"] = True
                    st.session_state["user_id"] = row[0]
                    st.session_state["username"] = row[1]
                    st.session_state["user_role"] = row[3]
                    st.session_state["logout_manual_flag"] = False
                    if "is_pro_cache" in st.session_state:
                        del st.session_state["is_pro_cache"]
                    return True
        except Exception as e:
            print(f"🔥 Auth Error: {e}", file=sys.stderr)
        return False

    @staticmethod
    def login_with_google(email: str, name: str = None):
        """Autenticación nativa Google OIDC mikey v7.15"""
        from db.session import engine
        try:
            with engine.connect() as conn:
                # 1. Buscar por email
                sql = text("SELECT id, username, role FROM users WHERE email = :e")
                user = conn.execute(sql, {"e": email}).first()
                
                if not user:
                    # 2. Intentar fusionar con cuenta 'cesar' legacy
                    sql_legacy = text("SELECT id FROM users WHERE (username = 'cesar' OR username = 'Cesar') AND (email IS NULL OR email = '')")
                    legacy_id = conn.execute(sql_legacy).scalar()
                    
                    if legacy_id:
                        # Transformar cuenta legacy en cuenta Google mikey
                        sql_up = text("UPDATE users SET email = :e, password_hash = 'GOOGLE_OAUTH' WHERE id = :uid")
                        with engine.begin() as t_conn:
                            t_conn.execute(sql_up, {"e": email, "uid": legacy_id})
                        user_id, user_name, user_role = legacy_id, "cesar", "user"
                    else:
                        # 3. Crear cuenta nueva
                        new_name = name if (name and name != "None") else email.split('@')[0]
                        sql_ins = text("INSERT INTO users (username, email, password_hash, role) VALUES (:u, :e, 'GOOGLE_OAUTH', 'user') RETURNING id")
                        with engine.begin() as t_conn:
                            user_id = t_conn.execute(sql_ins, {"u": new_name, "e": email}).scalar()
                        user_name, user_role = new_name, "user"
                else:
                    user_id, user_name, user_role = user
                    
                # 4. Fusión de Datos atómica (OPEC y Estadísticas) v7.15
                # Si el usuario no tiene OPEC, buscamos si 'cesar' legacy los tiene
                sql_check_opec = text("SELECT id FROM user_opec WHERE user_id = :uid LIMIT 1")
                if not conn.execute(sql_check_opec, {"uid": user_id}).first():
                    sql_legacy_id = text("SELECT id FROM users WHERE (username = 'cesar' OR username = 'Cesar') AND id != :curr_id")
                    leg_id = conn.execute(sql_legacy_id, {"curr_id": user_id}).scalar()
                    if leg_id:
                        with engine.begin() as t_conn:
                            t_conn.execute(text("DELETE FROM user_opec WHERE user_id = :uid"), {"uid": user_id})
                            t_conn.execute(text("DELETE FROM user_stats WHERE user_id = :uid"), {"uid": user_id})
                            t_conn.execute(text("UPDATE user_opec SET user_id = :new_uid WHERE user_id = :old_uid"), {"new_uid": user_id, "old_uid": leg_id})
                            t_conn.execute(text("UPDATE user_stats SET user_id = :new_uid WHERE user_id = :old_uid"), {"new_uid": user_id, "old_uid": leg_id})

                # 5. Iniciar Sesión en Streamlit
                st.query_params.clear()
                
                # Saneamiento de Identidad mikey v7.19
                # Prioridad máxima para forecesar@gmail.com
                if email == "forecesar@gmail.com" or user_name == "Aspirante" or not user_name:
                    user_name = "cesar"
                
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user_id
                st.session_state["username"] = user_name
                st.session_state["user_role"] = user_role
                st.session_state["logout_manual_flag"] = False
                return True
        except Exception as e:
            print(f"🔥 Google Login Error: {e}", file=sys.stderr)
            return False

    @staticmethod
    def logout():
        """Bala de Plata v7.21: Logout Nativo Streamlit (Sin JS Hacks)"""
        # 1. Limpieza de estado local (Borrar todo PRIMERO)
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # 2. Establecer banderas post-limpieza
        st.session_state["logout_manual_flag"] = True
        st.session_state["logged_in"] = False
        
        # 2. Intentar logout nativo OIDC (opcional, por si acaso)
        try:
            if hasattr(st, "logout"):
                st.logout()
        except:
            pass
            
        # 3. Redirección Nativa via Query Params + Switch Page
        st.query_params["logout"] = "1"
        try:
             st.switch_page("app.py")
        except Exception:
             st.rerun()

    @staticmethod
    def check_auth():
        """Guardián de Acceso v7.18"""
        # 0. El Muro del Logout (Si el parámetro está en la URL, BLOQUEO TOTAL)
        if st.query_params.get("logout") == "1":
            # Si hay una sesión activa, la limpiamos de forma atómica
            if st.session_state.get("logged_in"):
                st.session_state.clear()
            st.session_state["logout_manual_flag"] = True
            return False

        # 1. Sesión Local
        if st.session_state.get("logged_in"):
            return True

        # 2. Sesión Nativa (Google OIDC)
        native_user = getattr(st, "user", None)
        if native_user and native_user.is_logged_in:
            if not st.session_state.get("logout_manual_flag"):
                return AuthManager.login_with_google(native_user.email, native_user.name)
        
        return False

    @staticmethod
    def is_pro():
        """Verificar nivel PRO mikey v7.15"""
        if not st.session_state.get("user_id"):
            return False
        if st.session_state.get("user_role") == "admin":
            return True
        if "is_pro_cache" in st.session_state:
            return st.session_state["is_pro_cache"]
        
        from db.session import engine
        from datetime import datetime
        try:
            with engine.connect() as conn:
                sql = text("SELECT subscription_tier, subscription_expiry FROM users WHERE id = :uid")
                row = conn.execute(sql, {"uid": st.session_state["user_id"]}).first()
                is_pro_val = False
                if row and row[0] == "pro":
                    expiry = row[1]
                    if expiry:
                        if isinstance(expiry, str): expiry = datetime.fromisoformat(expiry)
                        is_pro_val = expiry > datetime.now()
                    else:
                        is_pro_val = True
                st.session_state["is_pro_cache"] = is_pro_val
                return is_pro_val
        except:
            return False
