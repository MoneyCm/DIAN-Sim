import sys

import streamlit as st
from sqlalchemy import text


def is_admin() -> bool:
    """Comprueba el rol actual directamente en la base de datos."""
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


def require_admin() -> None:
    """Detiene la página actual si la sesión no tiene rol administrativo."""
    from core.auth import AuthManager

    if not AuthManager.check_auth():
        st.warning("Acceso denegado. Inicia sesión para continuar.")
        st.stop()
    if not is_admin():
        st.error("No tienes permisos de administrador para ver esta página.")
        st.stop()