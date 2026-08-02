import bcrypt
import os
import sys
import time
import streamlit as st
from sqlalchemy import text
from datetime import datetime, timedelta

from core.auth_session import create_session_token, verify_session_token


AUTH_COOKIE = "dian_sim_session"
AUTH_TTL_SECONDS = 30 * 24 * 60 * 60


def _cookie_secret() -> str:
    try:
        return str(st.secrets["auth"]["cookie_secret"])
    except Exception:
        return os.getenv("AUTH_COOKIE_SECRET", "")


def _cookie_manager():
    try:
        import extra_streamlit_components as stx
        if "_auth_cookie_manager" not in st.session_state:
            st.session_state["_auth_cookie_manager"] = stx.CookieManager(
                key="dian_sim_auth_cookies"
            )
        return st.session_state["_auth_cookie_manager"]
    except ImportError:
        return None

class AuthManager:
    @staticmethod
    def _persist_login(user_id, username, role) -> None:
        manager = _cookie_manager()
        secret = _cookie_secret()
        if manager is None or not secret:
            return
        token = create_session_token(user_id, username, role, secret, AUTH_TTL_SECONDS)
        manager.set(
            AUTH_COOKIE,
            token,
            expires_at=datetime.now() + timedelta(seconds=AUTH_TTL_SECONDS),
            key="set_dian_sim_session",
        )

    @staticmethod
    def _restore_login() -> bool:
        manager = _cookie_manager()
        secret = _cookie_secret()
        if manager is None or not secret:
            return False
        token = manager.get(AUTH_COOKIE)
        payload = verify_session_token(token, secret)
        if not payload:
            return False
        from db.session import engine
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT username, role FROM users WHERE id = :uid"),
                    {"uid": payload["uid"]},
                ).first()
            if not row or row[0] != payload["username"]:
                return False
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = payload["uid"]
            st.session_state["username"] = row[0]
            st.session_state["user_role"] = row[1]
            st.session_state["logout_manual_flag"] = False
            return True
        except Exception as exc:
            print(f"Persistent session restore error: {exc}", file=sys.stderr)
            return False

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
        # Limitación básica por sesión para frenar intentos automatizados sin
        # introducir una tabla nueva ni bloquear permanentemente al usuario.
        now = time.time()
        attempts = st.session_state.setdefault("_login_attempts", {})
        state = attempts.get(str(username), {"count": 0, "locked_until": 0.0})
        if now < float(state.get("locked_until", 0.0)):
            return False
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
                    AuthManager._persist_login(row[0], row[1], row[3])
                    if "is_pro_cache" in st.session_state:
                        del st.session_state["is_pro_cache"]
                    attempts.pop(str(username), None)
                    return True
        except Exception as e:
            print(f"🔥 Auth Error: {e}", file=sys.stderr)
        state["count"] = int(state.get("count", 0)) + 1
        if state["count"] >= 5:
            state["locked_until"] = now + 60
            state["count"] = 0
        attempts[str(username)] = state
        return False

    @staticmethod
    def login_with_google(email: str, name: str = None):
        """Autentica por OIDC usando exclusivamente el email verificado."""
        from db.session import engine
        try:
            with engine.connect() as conn:
                user = conn.execute(
                    text("SELECT id, username, role FROM users WHERE email = :e"),
                    {"e": email},
                ).first()

                if user:
                    user_id, user_name, user_role = user
                else:
                    base_name = (name if name and name != "None" else email.split("@")[0]).strip()
                    base_name = base_name or "usuario"
                    new_name = base_name
                    suffix = 1
                    while conn.execute(
                        text("SELECT 1 FROM users WHERE username = :u"), {"u": new_name}
                    ).first():
                        suffix += 1
                        new_name = f"{base_name}-{suffix}"

                    with engine.begin() as insert_conn:
                        user_id = insert_conn.execute(
                            text(
                                "INSERT INTO users (username, email, password_hash, role) "
                                "VALUES (:u, :e, 'GOOGLE_OAUTH', 'user') RETURNING id"
                            ),
                            {"u": new_name, "e": email},
                        ).scalar()
                    user_name, user_role = new_name, "user"

                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user_id
                st.session_state["username"] = user_name
                st.session_state["user_role"] = user_role
                st.session_state["logout_manual_flag"] = False
                return True
        except Exception as exc:
            print(f"Google login error: {exc}", file=sys.stderr)
            return False

    @staticmethod
    def logout():
        """Bala de Plata v7.21: Logout Nativo Streamlit (Sin JS Hacks)"""
        manager = _cookie_manager()
        if manager is not None:
            try:
                manager.delete(AUTH_COOKIE, key="delete_dian_sim_session")
                time.sleep(0.15)
            except Exception:
                pass
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
        """Guardián de Acceso v7.18 (Debugged)"""
        # Debug Log
        q_params = st.query_params
        # print(f"🔐 CHECK_AUTH: Params detected: {q_params}")
        
        # 0. El Muro del Logout (Si el parámetro está en la URL, BLOQUEO TOTAL)
        # Check mas permisivo: si existe la key 'logout', asumimos intencion de salir
        if "logout" in q_params:
            # Si hay una sesión activa, la limpiamos de forma atómica
            if st.session_state.get("logged_in"):
                st.session_state.clear()
            st.session_state["logout_manual_flag"] = True
            return False

        # 1. Sesión Local
        if st.session_state.get("logged_in"):
            return True

        # Recupera el login local tras una reconexión móvil o suspensión de pestaña.
        if not st.session_state.get("logout_manual_flag") and AuthManager._restore_login():
            return True

        # 2. Sesión Nativa (Google OIDC)
        native_user = getattr(st, "user", None)
        if native_user and native_user.is_logged_in:
            if not st.session_state.get("logout_manual_flag"):
                return AuthManager.login_with_google(native_user.email, native_user.name)
        
        return False

    @staticmethod
    def is_admin() -> bool:
        """Comprueba el rol actual contra la base de datos."""
        user_id = st.session_state.get("user_id")
        if not user_id or not st.session_state.get("logged_in"):
            return False

        from db.session import engine
        try:
            with engine.connect() as conn:
                role = conn.execute(
                    text("SELECT role FROM users WHERE id = :uid"), {"uid": user_id}
                ).scalar()
            st.session_state["user_role"] = role
            return role == "admin"
        except Exception as exc:
            print(f"Admin authorization error: {exc}", file=sys.stderr)
            return False

    @staticmethod
    def require_admin() -> None:
        """Detiene la página actual si el usuario no es administrador."""
        if not AuthManager.check_auth():
            st.warning("Acceso denegado. Inicia sesión para continuar.")
            st.stop()
        if not AuthManager.is_admin():
            st.error("No tienes permisos de administrador para ver esta página.")
            st.stop()
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
