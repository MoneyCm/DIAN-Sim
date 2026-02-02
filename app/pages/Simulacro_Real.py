
import streamlit as st
import time
import datetime
import random
import os
import sys

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.orm import joinedload
from db.session import get_db
from db.models import CaseStudy, Question
from app.ui_utils import load_css as inject_custom_css

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Simulacro Real - DIAN",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="collapsed" # Real exam usually hides distractions
)

inject_custom_css()

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
<style>
    .case-text {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2e86c1;
        font-family: 'Georgia', serif;
        font-size: 1.1rem;
        line-height: 1.6;
        color: #2c3e50;
        height: 80vh;
        overflow-y: auto;
    }
    .timer-box {
        background-color: #e74c3c;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
        font-size: 1.5rem;
        position: fixed;
        top: 60px;
        right: 20px;
        z-index: 999;
    }
    .question-box {
        margin-bottom: 30px;
        padding: 15px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "exam_active" not in st.session_state:
    st.session_state.exam_active = False
if "exam_start_time" not in st.session_state:
    st.session_state.exam_start_time = None
if "exam_cases" not in st.session_state:
    st.session_state.exam_cases = []
if "current_case_idx" not in st.session_state:
    st.session_state.current_case_idx = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {} # {question_id: choice}

def load_exam_cases():
    db = next(get_db())
    # Load 3 random cases for the simulation
    # Use joinedload to fetch questions efficiently
    cases = db.query(CaseStudy).options(joinedload(CaseStudy.questions)).order_by(func.random()).limit(3).all()
    # Filter cases that actually have questions
    valid_cases = [c for c in cases if c.questions]
    db.close()
    return valid_cases

def start_exam():
    with st.spinner("Preparando entorno de examen..."):
        cases = load_exam_cases()
        if not cases:
            st.error("No hay suficientes 'Casos Protagónicos' generados aún. Por favor, genera casos primero.")
            return
        
        st.session_state.exam_cases = cases
        st.session_state.exam_active = True
        st.session_state.exam_start_time = datetime.datetime.now()
        st.session_state.current_case_idx = 0
        st.session_state.user_answers = {}
        st.rerun()

def finish_exam():
    # Calculate score
    correct = 0
    total = 0
    
    for case in st.session_state.exam_cases:
        for q in case.questions:
            user_choice = st.session_state.user_answers.get(q.question_id)
            if user_choice == q.correct_key:
                correct += 1
            total += 1
            
    st.session_state.exam_score = (correct, total)
    st.session_state.exam_active = False
    st.rerun()

# --- VISTA PRINCIPAL ---

if not st.session_state.exam_active:
    # --- PANTALLA DE INICIO ---
    st.title("⏱️ Simulacro de Alta Presión")
    st.markdown("""
    ### ⚠️ Modo Examen Real
    Este modo simula las condiciones exactas de la prueba de la CNSC/DIAN.
    
    *   **Formato:** Casos Protagónicos (1 Texto -> Múltiples Preguntas).
    *   **Tiempo:** Estricto (2 minutos promedio por pregunta).
    *   **Navegación:** No puedes volver a casos anteriores una vez terminados.
    *   **Ayudas:** Deshabilitadas (No verás la respuesta correcta inmediatamente).
    
    **¿Estás listo para probar tu nivel real?**
    """)
    
    if "exam_score" in st.session_state:
        c, t = st.session_state.exam_score
        pct = (c/t)*100 if t > 0 else 0
        st.success(f"### Resultado Final: {c}/{t} ({pct:.1f}%)")
        del st.session_state.exam_score
    
    if st.button("🔴 INICIAR EXAMEN AHORA", type="primary", use_container_width=True):
        start_exam()

else:
    # --- PANTALLA DE EXAMEN ---
    
    # 1. Timer Logic
    elapsed = datetime.datetime.now() - st.session_state.exam_start_time
    total_questions = sum(len(c.questions) for c in st.session_state.exam_cases)
    total_time_min = total_questions * 2 # 2 min per question
    remaining = datetime.timedelta(minutes=total_time_min) - elapsed
    
    if remaining.total_seconds() <= 0:
        st.warning("¡TIEMPO TERMINADO!")
        finish_exam()
    
    # Render Timer
    mins, secs = divmod(int(remaining.total_seconds()), 60)
    st.markdown(f'<div class="timer-box">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
    
    # 2. Global Progress
    current_idx = st.session_state.current_case_idx
    current_case = st.session_state.exam_cases[current_idx]
    
    st.progress((current_idx) / len(st.session_state.exam_cases))
    st.caption(f"Caso {current_idx + 1} de {len(st.session_state.exam_cases)}")
    
    # 3. Layout: Split Screen
    col_text, col_questions = st.columns([1, 1.2], gap="large")
    
    with col_text:
        st.markdown(f"### 📄 {current_case.title or 'Situación'}")
        st.markdown(f'<div class="case-text">{current_case.text}</div>', unsafe_allow_html=True)
        st.info("💡 Lee atentamente el texto. Todas las preguntas de la derecha se basan en esta información.")

    with col_questions:
        st.markdown("### ❓ Preguntas del Caso")
        for i, q in enumerate(current_case.questions):
            st.markdown(f"#### Pregunta {i+1}")
            st.write(q.stem)
            
            opts = q.options_json
            options_list = list(opts.keys())
            
            # Key for state
            k = f"q_{q.question_id}"
            
            # Radio
            # We need to map options to a display format
            # Use index if already selected
            prev_sel = st.session_state.user_answers.get(q.question_id)
            idx = options_list.index(prev_sel) if prev_sel in options_list else None
            
            sel = st.radio(
                "Seleccione una opción:",
                options_list,
                format_func=lambda x: f"{x}) {opts[x]}",
                key=k,
                index=idx,
                label_visibility="collapsed"
            )
            
            # Save selection immediately
            if sel:
                st.session_state.user_answers[q.question_id] = sel
            
            st.divider()
        
        # Navigation Buttons
        c1, c2 = st.columns(2)
        is_last = (current_idx == len(st.session_state.exam_cases) - 1)
        
        if c2.button("Siguiente Caso ➡️" if not is_last else "FINALIZAR EXAMEN 🏁", type="primary", use_container_width=True):
            if is_last:
                finish_exam()
            else:
                st.session_state.current_case_idx += 1
                st.rerun()

