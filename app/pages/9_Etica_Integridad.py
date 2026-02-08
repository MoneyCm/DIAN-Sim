import streamlit as st
import os
import sys
import json

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import Question
from ui_utils import load_css, render_header, render_custom_sidebar
from core.auth import AuthManager
import uuid
from core.dedupe import compute_hash
import datetime

st.set_page_config(page_title="Ética e Integridad | DIAN Sim", page_icon="⚖️", layout="wide")

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión.")
    st.stop()

load_css()
render_header(title="Módulo de Ética e Integridad", subtitle="Preparación para evaluación de valores institucionales (10-15% del examen)")

# Load ethics data
ethics_path = os.path.join(PROJECT_ROOT, "data", "codigo_etica_dian.json")
with open(ethics_path, "r", encoding="utf-8") as f:
    ethics_data = json.load(f)

st.markdown("""
<div class="dian-card">
    <h3>📋 Sobre esta evaluación</h3>
    <p>Las preguntas de <b>Ética e Integridad</b> representan el <b>10-15% del examen</b> de la DIAN. 
    Utilizan la metodología de <b>Escala Likert</b> para medir tu alineación con los valores institucionales.</p>
    
    <p><b>Valores Institucionales DIAN:</b> Honestidad, Respeto, Compromiso, Diligencia, Justicia, Transparencia</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Sidebar info
stats_s, rank = render_custom_sidebar()

# Mode selection
mode = st.radio("Modo de Práctica:", ["📖 Aprender Código de Ética", "✍️ Simulacro de Integridad"], horizontal=True)

if mode == "📖 Aprender Código de Ética":
    st.subheader("📚 Código de Ética DIAN")
    
    # Display principles
    for key, principio in ethics_data["principios_eticos"].items():
        with st.expander(f"**{principio['nombre']}**", expanded=False):
            st.write(f"**Descripción:** {principio['descripcion']}")
            st.write("**Conductas Esperadas:**")
            for conducta in principio["conductas_esperadas"]:
                st.write(f"- {conducta}")
    
    st.divider()
    st.subheader("🎯 Criterios de Evaluación")
    
    for criterio, descripcion in ethics_data["respuestas_correctas"]["criterios"].items():
        st.markdown(f"**{criterio.replace('_', ' ').title()}:** {descripcion}")

else:  # Simulacro mode
    st.subheader("✍️ Simulacro de Integridad")
    
    # Configuration
    col1, col2 = st.columns(2)
    with col1:
        categoria = st.selectbox("Categoría:", 
            ["Todas"] + [s["categoria"] for s in ethics_data["situaciones_eticas_comunes"]])
    with col2:
        num_preguntas = st.slider("Número de preguntas:", 5, 30, 12)
    
    if st.button("🚀 Iniciar Simulacro de Integridad", type="primary", use_container_width=True):
        # Collect questions
        all_afirmaciones = []
        for situacion in ethics_data["situaciones_eticas_comunes"]:
            if categoria == "Todas" or situacion["categoria"] == categoria:
                for afirmacion in situacion["afirmaciones"]:
                    all_afirmaciones.append({
                        "categoria": situacion["categoria"],
                        "afirmacion": afirmacion
                    })
        
        # Sample questions
        import random
        selected = random.sample(all_afirmaciones, min(num_preguntas, len(all_afirmaciones)))
        
        st.session_state["ethics_questions"] = selected
        st.session_state["ethics_answers"] = {}
        st.session_state["ethics_started"] = True
        st.rerun()
    
    # Display questions if started
    if st.session_state.get("ethics_started"):
        questions = st.session_state.get("ethics_questions", [])
        
        st.markdown(f"### Responde las siguientes {len(questions)} afirmaciones")
        st.info("💡 **Instrucciones:** Indica tu nivel de acuerdo con cada afirmación según el Código de Ética DIAN.")
        
        for i, q in enumerate(questions):
            st.markdown(f"---")
            st.markdown(f"**Pregunta {i+1} de {len(questions)}**")
            st.markdown(f"**Categoría:** {q['categoria']}")
            st.markdown(f"### {q['afirmacion']}")
            
            answer = st.radio(
                "Tu respuesta:",
                options=[
                    "1 - Totalmente en desacuerdo",
                    "2 - En desacuerdo",
                    "3 - Neutral",
                    "4 - De acuerdo",
                    "5 - Totalmente de acuerdo"
                ],
                key=f"ethics_q_{i}",
                horizontal=False
            )
            
            st.session_state["ethics_answers"][i] = answer
        
        st.markdown("---")
        
        if len(st.session_state.get("ethics_answers", {})) == len(questions):
            if st.button("✅ Finalizar y Ver Resultados", type="primary", use_container_width=True):
                st.session_state["ethics_completed"] = True
                st.rerun()
        else:
            st.warning(f"Responde todas las preguntas para continuar ({len(st.session_state.get('ethics_answers', {}))} de {len(questions)})")
    
    # Show results
    if st.session_state.get("ethics_completed"):
        st.success("✅ Simulacro completado")
        st.markdown("### 📊 Análisis de Respuestas")
        
        st.info("""
        **Nota Importante:** Este es un simulacro de práctica. Las respuestas "correctas" en ética dependen del 
        contexto y la interpretación del Código de Ética DIAN. 
        
        **Criterios generales:**
        - **Conflicto de intereses:** Siempre declarar y abstenerse
        - **Información privilegiada:** Uso estrictamente institucional
        - **Regalos:** Rechazar cualquier obsequio
        - **Transparencia:** Documentar todas las actuaciones
        - **Recursos públicos:** Uso exclusivo institucional
        - **Imparcialidad:** Decisiones basadas solo en criterios técnicos
        """)
        
        questions = st.session_state.get("ethics_questions", [])
        answers = st.session_state.get("ethics_answers", {})
        
        # Display answers
        for i, q in enumerate(questions):
            with st.expander(f"Pregunta {i+1}: {q['categoria']}", expanded=False):
                st.write(f"**Afirmación:** {q['afirmacion']}")
                st.write(f"**Tu respuesta:** {answers.get(i, 'No respondida')}")
                
                # Provide guidance based on category
                cat = q['categoria']
                criterios = ethics_data["respuestas_correctas"]["criterios"]
                
                if "Conflicto" in cat:
                    st.info(f"💡 **Criterio:** {criterios['conflicto_intereses']}")
                elif "Información" in cat:
                    st.info(f"💡 **Criterio:** {criterios['informacion_privilegiada']}")
                elif "Regalos" in cat or "Dádivas" in cat:
                    st.info(f"💡 **Criterio:** {criterios['regalos_dadivas']}")
                elif "Transparencia" in cat:
                    st.info(f"💡 **Criterio:** {criterios['transparencia']}")
                elif "Recursos" in cat:
                    st.info(f"💡 **Criterio:** {criterios['recursos_publicos']}")
                elif "Imparcialidad" in cat:
                    st.info(f"💡 **Criterio:** {criterios['imparcialidad']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Nuevo Simulacro"):
                for key in ["ethics_questions", "ethics_answers", "ethics_started", "ethics_completed"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        with col2:
            if st.button("📚 Revisar Código de Ética"):
                for key in ["ethics_questions", "ethics_answers", "ethics_started", "ethics_completed"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

st.divider()
st.caption("⚖️ **Fuente:** Código de Ética DIAN y Guía de Orientación al Aspirante (GOA) - CNSC")
