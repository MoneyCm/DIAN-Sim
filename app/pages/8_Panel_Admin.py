import streamlit as st
import os, sys, pandas as pd
from sqlalchemy import func

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import User, UserStats, UserOPEC, Attempt, Question, QuestionAnkiEnrichment
from ui_utils import load_css, render_header
from core.access_control import require_admin
from core.normativa import NormativaManager
from core.anki_enrichment import backfill_enrichments
from core.config import get_api_key

# pass # Removed st.set_page_config

require_admin()

load_css()
render_header(title="Panel de Administración Maestro", subtitle="Gestión global de usuarios, leyes e inteligencia. Mikey")

tab_stats, tab_users, tab_normativa, tab_anki = st.tabs(["📊 Estadísticas Globales", "👥 Gestión de Usuarios", "🏛️ Inteligencia Normativa", "🎴 Enriquecimiento Anki"])

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
    
    files = [f for f in os.listdir(norm_path) if f.endswith(".pdf")]
    if files:
        st.write("Archivos indexados actualmente:")
        for f in files:
            st.write(f"- 📄 {f}")
    else:
        st.write("La biblioteca está vacía.")
    
    st.divider()
    
    # --- ACCIONES DE INDEXACIÓN ---
    st.subheader("⚙️ Acciones de Sincronización RAG")
    col_act1, col_act2 = st.columns(2)
    
    with col_act1:
        if st.button("🔄 Indexar Biblioteca (Leer PDFs)", use_container_width=True, help="Extrae el texto de los PDFs locales y los guarda en la base de datos"):
            manager = NormativaManager()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_cb(pct, msg):
                progress_bar.progress(pct / 100.0)
                status_text.text(msg)
                
            try:
                indexed = manager.index_all(progress_callback=progress_cb)
                st.success(f"¡Proceso completado! Se indexaron {indexed} nuevos fragmentos de ley.")
                st.rerun()
            except Exception as e:
                st.error(f"Error indexando PDFs: {e}")
                
    with col_act2:
        if st.button("🧠 Calcular Vectores Semánticos", use_container_width=True, help="Genera embeddings vectoriales de Gemini para la búsqueda inteligente"):
            manager = NormativaManager()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_cb(pct, msg):
                progress_bar.progress(pct / 100.0)
                status_text.text(msg)
                
            try:
                updated = manager.backfill_embeddings(progress_callback=progress_cb)
                st.success(f"¡Sincronización vectorial completa! Se generaron vectores para {updated} fragmentos.")
            except Exception as e:
                st.error(f"Error generando embeddings: {e}")

    st.divider()
    st.subheader("📤 Subir Nueva Ley")
    uploaded_file = st.file_uploader("Sube el PDF de la Ley o Estatuto", type="pdf")
    if uploaded_file is not None:
        with open(os.path.join(norm_path, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Auto-indexar tras la subida
        manager = NormativaManager()
        try:
            indexed = manager.index_all()
            st.success(f"¡{uploaded_file.name} subido e indexado! Se crearon {indexed} fragmentos. Haz clic en 'Calcular Vectores Semánticos' para activar la búsqueda vectorial sobre esta nueva ley. Mikey")
            st.balloons()
        except Exception as e:
            st.error(f"Error indexando automáticamente el nuevo PDF: {e}")

# --- TAB: ANKI ENRICHMENT ---
with tab_anki:
    st.subheader("🎴 Enriquecimiento pedagógico para Anki")
    db_anki = SessionLocal()
    try:
        generated_count = db_anki.query(QuestionAnkiEnrichment).filter(
            QuestionAnkiEnrichment.status.in_(["generated", "reviewed"])
        ).count()
        error_count = db_anki.query(QuestionAnkiEnrichment).filter_by(status="error").count()
        total_questions_anki = db_anki.query(Question).count()
    finally:
        db_anki.close()

    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    col_a1.metric("Preguntas", total_questions_anki)
    col_a2.metric("Enriquecidas", generated_count)
    col_a3.metric("Pendientes", max(total_questions_anki - generated_count, 0))
    col_a4.metric("Errores", error_count)

    provider_anki = st.selectbox(
        "Proveedor LLM", ["Gemini", "OpenAI", "Groq", "Mistral"], key="admin_anki_provider"
    )
    batch_limit = st.number_input(
        "Máximo de preguntas en esta ejecución", min_value=1, max_value=500, value=25, step=5
    )
    force_regeneration = st.checkbox(
        "Regenerar contenido no revisado",
        value=False,
        help="Los enriquecimientos revisados nunca se sobrescriben.",
    )

    if st.button("🧠 Ejecutar backfill Anki", type="primary", use_container_width=True):
        provider_key = provider_anki.lower()
        api_key_anki = get_api_key(provider_key)
        if not api_key_anki:
            st.error(f"No hay una API key global configurada para {provider_anki}.")
        else:
            progress_anki = st.progress(0)
            status_anki = st.empty()

            def progress_anki_cb(pct, message):
                progress_anki.progress(pct / 100.0)
                status_anki.text(message)

            result = backfill_enrichments(
                SessionLocal,
                provider_key,
                api_key_anki,
                limit=int(batch_limit),
                force=force_regeneration,
                progress_callback=progress_anki_cb,
            )
            if result["errors"]:
                st.warning(
                    f"Generadas: {result['generated']} de {result['total']}. Errores: {result['errors']}."
                )
            else:
                st.success(f"Se enriquecieron {result['generated']} preguntas.")
            st.rerun()
st.divider()
st.caption("🔒 Este panel es de uso exclusivo para el propietario de la plataforma. Mikey")
