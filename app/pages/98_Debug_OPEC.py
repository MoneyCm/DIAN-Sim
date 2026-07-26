import streamlit as st
import pandas as pd
from db.session import SessionLocal
from db.models import UserOPEC, User
from core.auth import AuthManager

# pass # Removed st.set_page_config

AuthManager.require_admin()

st.title("🔧 Diagnóstico de OPEC")


u_id = st.session_state["user_id"]
st.write(f"**User ID en Sesión:** `{u_id}`")

db = SessionLocal()
try:
    user = db.query(User).get(u_id)
    if user:
        st.write(f"**Usuario DB:** `{user.username}` (ID: {user.id})")
    else:
        st.error("Usuario no encontrado en DB")

    st.subheader("OPECs Registradas")
    opecs = db.query(UserOPEC).filter_by(user_id=u_id).all()
    
    if opecs:
        data = []
        for o in opecs:
            data.append({
                "ID": o.id,
                "OPEC Num": o.opec_number,
                "Cargo": o.job_title,
                "Es Activo (True/False)": o.is_active,
                "Tipo de Dato is_active": type(o.is_active)
            })
        st.table(data)
        
        active = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
        st.subheader("Resultado Query 'is_active=True'")
        if active:
            st.success(f"✅ Se encontró activo: {active.job_title} (ID: {active.id})")
        else:
            st.error("❌ La consulta `filter_by(is_active=True)` devolvió None.")
    else:
        st.warning("No se encontraron registros en UserOPEC para este usuario.")

finally:
    db.close()
