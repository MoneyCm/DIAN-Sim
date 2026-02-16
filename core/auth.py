import bcrypt
import os
import streamlit as st
from sqlalchemy.orm import Session
try:
    from db.models import User, UserOPEC, Attempt, UserStats, Achievement, Skill, QuestionPerformance
    from db.session import SessionLocal, engine
except ImportError:
    # Fallback para entornos donde el path aún se está configurando
    pass

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
                    # Resetear flags de sesión mikey v7.5
                    st.session_state["logout_manual_flag"] = False
                    if "is_pro_cache" in st.session_state:
                        del st.session_state["is_pro_cache"]
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
                    # mikey v7.0: Buscar cuenta legacy 'cesar' sin email
                    sql_legacy = text("SELECT id, username, role FROM users WHERE username = 'cesar' AND (email IS NULL OR email = '')")
                    legacy_row = conn.execute(sql_legacy).first()
                    
                    if legacy_row:
                        user_id, user_name, user_role = legacy_row
                        sql_update = text("UPDATE users SET email = :e, password_hash = 'GOOGLE_OAUTH' WHERE id = :uid")
                        with engine.begin() as t_conn:
                            t_conn.execute(sql_update, {"e": email, "uid": user_id})
                    else:
                        # mikey v7.8: Asegurar que el username nunca sea 'None'
                        base_username = username if (username and username != "None") else email.split('@')[0]
                        sql_ins = text("INSERT INTO users (username, email, password_hash, role) VALUES (:u, :e, 'GOOGLE_OAUTH', 'user') RETURNING id")
                        with engine.begin() as t_conn:
                            new_id = t_conn.execute(sql_ins, {"u": base_username, "e": email}).scalar()
                            user_id, user_name, user_role = new_id, base_username, "user"
                else:
                    user_id, user_name, user_role = user_row
                    # mikey v7.8: Corregir nombres 'None' en caliente
                    if not user_name or user_name == "None":
                        user_name = email.split('@')[0]
                        sql_up_name = text("UPDATE users SET username = :u WHERE id = :uid")
                        with engine.begin() as t_conn:
                            t_conn.execute(sql_up_name, {"u": user_name, "uid": user_id})
                        print(f"🛠️ [AUTH] Nombre 'None' de {email} corregido a {user_name}. Mikey.", file=sys.stderr)
                    
                            # mikey v7.14: Fusión Atómica Definitiva (OPEC + Stats)
                            sql_del_empty_opec = text("DELETE FROM user_opec WHERE user_id = :new_uid")
                            sql_del_empty_stats = text("DELETE FROM user_stats WHERE user_id = :new_uid")
                            sql_transfer_opec = text("UPDATE user_opec SET user_id = :new_uid WHERE user_id = :old_uid")
                            sql_transfer_stats = text("UPDATE user_stats SET user_id = :new_uid WHERE user_id = :old_uid")
                            sql_update_name = text("UPDATE users SET username = 'cesar' WHERE id = :new_uid")
                            
                            with engine.begin() as t_conn:
                                # 1. Limpiar rastro de la cuenta Gmail nueva (que está vacía)
                                t_conn.execute(sql_del_empty_opec, {"new_uid": user_id})
                                t_conn.execute(sql_del_empty_stats, {"new_uid": user_id})
                                # 2. Transferir datos de la cuenta legacy
                                t_conn.execute(sql_transfer_opec, {"new_uid": user_id, "old_uid": legacy_id})
                                t_conn.execute(sql_transfer_stats, {"new_uid": user_id, "old_uid": legacy_id})
                                # 3. Asegurar nombre 'cesar' en la cuenta vinculada
                                t_conn.execute(sql_update_name, {"new_uid": user_id})
                                user_name = "cesar"
                            
                            print(f"🚛 [AUTH] Fusión v7.14: 'cesar' -> {email}. Nombre fijado. Mikey.", file=sys.stderr)
                
                # mikey v7.13: Limpiar ABSOLUTAMENTE TODO rastro de logout al entrar con éxito
                if "logout" in st.query_params:
                    del st.query_params["logout"]
                st.query_params.clear()
                
                # Iniciar sesión en Streamlit
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user_id
                st.session_state["username"] = user_name
                st.session_state["user_role"] = user_role
                # Resetear flags de sesión mikey v7.5
                st.session_state["logout_manual_flag"] = False
                # Resetear caché de Pro
                if "is_pro_cache" in st.session_state:
                    del st.session_state["is_pro_cache"]
                return True
        except Exception as e:
            print(f"🔥 Google Auth Error mikey v6.0: {e}")
            return False

    @staticmethod
    def logout():
        """Cierre de sesión definitivo vía navegador mikey v7.14"""
        # 1. Parámetro persistente en URL
        st.query_params["logout"] = "1"
        
        # 2. Limpieza de sesión
        st.session_state.clear()
        st.session_state["logout_manual_flag"] = True
        
        # 3. Forzar salida nativa y REFRESO DE NAVEGADOR
        try:
            if hasattr(st, "logout"):
                st.logout()
        except:
            pass
        
        # Mikey v7.14: La bala de plata. Refresco por HTML para romper el bucle OIDC.
        st.markdown('<meta http-equiv="refresh" content="0; url=/?logout=1">', unsafe_allow_html=True)
        st.stop()

    @staticmethod
    def check_auth():
        # mikey v7.13: EL BLOQUEO MAESTRO
        # Si la URL dice que estamos fuera, LIMPIAR TODO y NO dejar entrar.
        if st.query_params.get("logout") == "1":
            st.session_state.clear()
            st.session_state["logout_manual_flag"] = True
            return False

        # 1. Login Manual
        manual_login = st.session_state.get("logged_in", False)
        
        # 2. Login Nativo (Streamlit OIDC) mikey v3.0
        native_user = getattr(st, "user", None)
        native_login = native_user.is_logged_in if native_user else False
        
        # Bypass de bucle si el usuario acaba de cerrar sesión manualmente
        if st.session_state.get("logout_manual_flag"):
            return manual_login
            
        if native_login and not manual_login:
            # Sincronizar login nativo con sesión local mikey
            AuthManager.login_with_google(st.user.email, st.user.name)
            return True
        return manual_login

    @staticmethod
    def is_pro():
        """Verifica si el usuario actual es PRO con máxima resiliencia mikey v7.3"""
        if "user_id" not in st.session_state or not st.session_state["user_id"]:
            return False
            
        if st.session_state.get("user_role") == "admin":
            return True

        # Caché de sesión para evitar consultas repetitivas
        if "is_pro_cache" in st.session_state:
            return st.session_state["is_pro_cache"]
            
        try:
            from sqlalchemy import text
            from datetime import datetime
            from db.session import engine
            
            with engine.connect() as conn:
                # Mikey v7.3: Consulta directa. Si la columna no existe, SQLAlchemy lanzará ProgrammingError 
                # y nuestro except lo atrapará devolviendo False (Free User) de forma segura.
                sql = text("SELECT subscription_tier, subscription_expiry FROM users WHERE id = :uid")
                row = conn.execute(sql, {"uid": st.session_state["user_id"]}).first()
                is_pro_val = False
                if row:
                    tier, expiry = row[0], row[1]
                    if tier == "pro":
                        if expiry:
                            if isinstance(expiry, str):
                                expiry = datetime.fromisoformat(expiry)
                            is_pro_val = expiry > datetime.now()
                        else:
                            is_pro_val = True
                
                st.session_state["is_pro_cache"] = is_pro_val
                return is_pro_val
        except Exception:
            # Fallback definitivo: Ante CUALQUIER error (DB cerrada, columna falta, etc.) -> FREE
            return False
