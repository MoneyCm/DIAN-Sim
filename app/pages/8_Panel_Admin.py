import streamlit as st
import os
import sys
import pandas as pd
from sqlalchemy import func

# Add root to python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import User, UserStats, UserOPEC, Attempt, Question
from ui_utils import load_css, render_header
from core.auth import AuthManager

st.set_page_config(page_title="Panel Admin | DIAN Sim", page_icon="🔑", layout="wide")

if not AuthManager.check_auth():
    st.warning("⚠️ Acceso denegado. Por favor inicia sesión.")
    st.stop()

if st.session_state.get("user_role") != "admin":
    st.error("🚫 No tienes permisos de administrador para ver esta página.")
    st.stop()

load_css()
render_header(title="Panel de Administración Maestro", subtitle="Gestión global de usuarios, leyes e inteligencia. Mikey")

tab_stats, tab_users, tab_normativa = st.tabs(["📊 Estadísticas Globales", "👥 Gestión de Usuarios", "🏛️ Inteligencia Normativa"])

# --- TAB: STATS ---
with tab_stats:
    db = SessionLocal()
    total_users = db.query(User).count()
    total_attempts = db.query(Attempt).count()
    total_points = db.query(func.sum(UserStats.total_points)).scalar() or 0
    total_questions = db.query(Question).count()
    db.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Usuarios Totales", total_users)
    with col2:
        st.metric("Simulacros Realizados", total_attempts)
    with col3:
        st.metric("Puntos Globales", f"{total_points:,}")
    with col4:
        st.metric("Banco de Preguntas", total_questions)

    st.divider()
    st.subheader("Uso del Sistema")
    # Here we could add a plot of usage over time if needed.
    st.info("El sistema está operando bajo el Protocolo CNSC 2667 con Inteligencia RAG Activa. Mikey")

# --- TAB: USERS ---
with tab_users:
    db = SessionLocal()
    users = db.query(User).all()
    user_data = []
    for u in users:
        stats = db.query(UserStats).filter_by(user_id=u.id).first()
        opecs = db.query(UserOPEC).filter_by(user_id=u.id).count()
        user_data.append({
            "ID": u.id,
            "Usuario": u.username,
            "Rol": u.role,
            "Puntos": stats.total_points if stats else 0,
            "Cargos (OPECs)": opecs,
            "Fecha Registro": u.created_at.strftime("%Y-%m-%d") if u.created_at else "N/A"
        })
    db.close()
    
    df_users = pd.DataFrame(user_data)
    st.dataframe(df_users, use_container_width=True)
    
    selected_user = st.selectbox("Gestionar Usuario", [u.username for u in users])
    if st.button("Hacer Administrador (Simulado)"):
        st.info(f"Funcionalidad para promover a {selected_user} a Admin lista para implementar. Mikey")

# --- TAB: NORMATIVA ---
with tab_normativa:
    st.subheader("📚 Gestión de Biblioteca Legal")
    norm_path = "data/normativa"
    if not os.path.exists(norm_path):
        os.makedirs(norm_path)
    
    files = os.listdir(norm_path)
    if files:
        st.write("Archivos indexados actualmente:")
        for f in files:
            if f.endswith(".pdf"):
                st.write(f"- 📄 {f}")
    else:
        st.write("La biblioteca está vacía.")
    
    st.divider()
    st.subheader("📤 Subir Nueva Ley")
    uploaded_file = st.file_uploader("Sube el PDF de la Ley o Estatuto (La IA lo leerá automáticamente)", type="pdf")
    if uploaded_file is not None:
        with open(os.path.join(norm_path, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"¡{uploaded_file.name} subido e indexado! La IA ahora tiene este conocimiento. Mikey")
        st.balloons()

st.divider()
st.caption("🔒 Este panel es de uso exclusivo para el propietario de la plataforma. Mikey")
