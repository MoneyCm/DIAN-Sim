import streamlit as st
import os, sys
import random

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import Question, QuestionPerformance
from ui_utils import load_css, render_header, render_favorite_button, render_custom_sidebar
from core.auth import AuthManager

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Inicia sesión para ver tu banco de errores y favoritos.")
    st.stop()

load_css()
render_custom_sidebar()
render_header(title="Centro de Repaso Especial", subtitle="Tus puntos débiles y favoritos en un solo lugar")

user_id = st.session_state.get("user_id")

tab1, tab2 = st.tabs(["❌ Banco de Errores", "⭐ Mis Favoritos"])

with tab1:
    st.markdown("### 🔍 Preguntas Falladas")
    st.info("Aquí aparecen las preguntas donde has tenido al menos un fallo. ¡Es hora de dominarlas!")
    
    db = SessionLocal()
    try:
        # Errores: misses > 0
        error_perf = db.query(QuestionPerformance).filter(
            QuestionPerformance.user_id == user_id,
            QuestionPerformance.misses > 0
        ).order_by(QuestionPerformance.misses.desc()).all()
        
        if not error_perf:
            st.success("✨ ¡Excelente! No tienes errores registrados en tu historial reciente.")
        else:
            for p in error_perf:
                q = db.query(Question).get(p.question_id)
                if q:
                    with st.expander(f"🔴 Fallos: {p.misses} | {q.topic}"):
                        st.markdown(f"**Enunciado:** {q.stem}")
                        st.markdown(f"**ID:** `{q.question_id}`")
                        st.success(f"✔️ **Correcta:** {q.correct_key}) {q.options_json.get(q.correct_key)}")
                        st.info(f"💡 **Retroalimentación:** {q.rationale}")
                        render_favorite_button(q.question_id, user_id)
    finally:
        db.close()

with tab2:
    st.markdown("### ⭐ Preguntas Favoritas")
    st.info("Preguntas que marcaste manualmente para repasar.")
    
    db = SessionLocal()
    try:
        fav_perf = db.query(QuestionPerformance).filter(
            QuestionPerformance.user_id == user_id,
            QuestionPerformance.is_favorite == True
        ).all()
        
        if not fav_perf:
            st.info("No has marcado ninguna pregunta como favorita todavía.")
        else:
            for p in fav_perf:
                q = db.query(Question).get(p.question_id)
                if q:
                    with st.expander(f"⭐ {q.topic}"):
                        st.markdown(f"**Enunciado:** {q.stem}")
                        st.markdown(f"**ID:** `{q.question_id}`")
                        st.success(f"✔️ **Correcta:** {q.correct_key}) {q.options_json.get(q.correct_key)}")
                        st.info(f"💡 **Retroalimentación:** {q.rationale}")
                        render_favorite_button(q.question_id, user_id)
    finally:
        db.close()

# Footer Action
st.divider()
st.markdown("### 🚀 Práctica Enfocada")
col1, col2 = st.columns(2)

if col1.button("💪 Iniciar Entrenamiento de Errores", use_container_width=True):
    db = SessionLocal()
    error_ids = [p.question_id for p in db.query(QuestionPerformance).filter(QuestionPerformance.user_id == user_id, QuestionPerformance.misses > 0).all()]
    db.close()
    if error_ids:
        st.session_state["exam_mode"] = True
        st.session_state["exam_questions"] = random.sample(error_ids, min(len(error_ids), 10))
        st.session_state["current_idx"] = 0
        st.session_state["answers"] = {}
        st.switch_page("pages/2_Ejecucion.py")
    else:
        st.error("No hay errores suficientes para un entrenamiento.")

if col2.button("⭐ Repasar mis Favoritas", use_container_width=True):
    db = SessionLocal()
    fav_ids = [p.question_id for p in db.query(QuestionPerformance).filter(QuestionPerformance.user_id == user_id, QuestionPerformance.is_favorite == True).all()]
    db.close()
    if fav_ids:
        st.session_state["exam_mode"] = True
        st.session_state["exam_questions"] = random.sample(fav_ids, min(len(fav_ids), 10))
        st.session_state["current_idx"] = 0
        st.session_state["answers"] = {}
        st.switch_page("pages/2_Ejecucion.py")
    else:
        st.error("Aún no tienes favoritas para repasar.")
