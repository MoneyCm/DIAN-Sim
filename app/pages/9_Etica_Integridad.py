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
    col1, col2, col3 = st.columns(3)
    with col1:
        categoria = st.selectbox("Categoría:", 
            ["Todas"] + [s["categoria"] for s in ethics_data["situaciones_eticas_comunes"]])
    with col2:
        num_preguntas = st.slider("Número de preguntas:", 5, 30, 12)
    with col3:
        use_ai = st.toggle("🤖 Generar con IA", value=False, help="Usa IA para generar afirmaciones nuevas y adaptativas")
    
    if st.button("🚀 Iniciar Simulacro de Integridad", type="primary", use_container_width=True):
        all_afirmaciones = []
        
        if use_ai:
            # Generar con IA
            with st.spinner("🤖 Generando afirmaciones éticas con IA..."):
                try:
                    from core.generators.ethics_generator import generate_ethics_statements, detect_weak_categories
                    from core.generators.llm import LLMGenerator
                    from core.config import get_api_key
                    
                    # Obtener API key del usuario
                    provider = "gemini"  # Por defecto
                    api_key = get_api_key(provider)
                    
                    if not api_key:
                        st.error("⚠️ No se encontró API key. Configura tu API key en el Generador IA primero.")
                        st.stop()
                    
                    # Detectar categorías débiles del usuario
                    db = SessionLocal()
                    user_id = st.session_state.get("user_id")
                    weak_categories = detect_weak_categories(user_id, db)
                    db.close()
                    
                    if weak_categories:
                        st.info(f"🎯 **Enfoque adaptativo:** Generando más preguntas en tus áreas de mejora: {', '.join(weak_categories)}")
                    
                    # Crear generador LLM
                    llm_gen = LLMGenerator(provider=provider, api_key=api_key)
                    
                    # Generar afirmaciones
                    if categoria == "Todas":
                        # Generar para todas las categorías proporcionalmente
                        categorias = [s["categoria"] for s in ethics_data["situaciones_eticas_comunes"]]
                        
                        # Priorizar categorías débiles
                        if weak_categories:
                            # 60% de preguntas en categorías débiles, 40% en el resto
                            weak_count = int(num_preguntas * 0.6)
                            normal_count = num_preguntas - weak_count
                            
                            # Generar para categorías débiles
                            per_weak = max(2, weak_count // len(weak_categories))
                            for cat in weak_categories:
                                statements = generate_ethics_statements(llm_gen, cat, per_weak, weak_categories)
                                all_afirmaciones.extend(statements)
                            
                            # Generar para otras categorías
                            other_cats = [c for c in categorias if c not in weak_categories]
                            if other_cats:
                                per_other = max(1, normal_count // len(other_cats))
                                for cat in other_cats:
                                    statements = generate_ethics_statements(llm_gen, cat, per_other)
                                    all_afirmaciones.extend(statements)
                        else:
                            # Sin debilidades detectadas, distribución uniforme
                            per_category = max(2, num_preguntas // len(categorias))
                            for cat in categorias:
                                statements = generate_ethics_statements(llm_gen, cat, per_category)
                                all_afirmaciones.extend(statements)
                    else:
                        # Generar solo para la categoría seleccionada
                        statements = generate_ethics_statements(llm_gen, categoria, num_preguntas, weak_categories)
                        all_afirmaciones.extend(statements)
                    
                    # Limitar al número solicitado
                    import random
                    if len(all_afirmaciones) > num_preguntas:
                        all_afirmaciones = random.sample(all_afirmaciones, num_preguntas)
                    
                    if not all_afirmaciones:
                        st.error("❌ No se pudieron generar afirmaciones con IA. Usando banco estático.")
                        use_ai = False
                except Exception as e:
                    st.error(f"❌ Error al generar con IA: {e}")
                    st.info("📚 Usando banco de afirmaciones estático.")
                    use_ai = False
        
        if not use_ai or not all_afirmaciones:
            # Usar banco estático
            for situacion in ethics_data["situaciones_eticas_comunes"]:
                if categoria == "Todas" or situacion["categoria"] == categoria:
                    for afirmacion in situacion["afirmaciones"]:
                        all_afirmaciones.append({
                            "categoria": situacion["categoria"],
                            "afirmacion": afirmacion
                        })
            
            # Sample questions
            import random
            all_afirmaciones = random.sample(all_afirmaciones, min(num_preguntas, len(all_afirmaciones)))
        
        st.session_state["ethics_questions"] = all_afirmaciones
        st.session_state["ethics_answers"] = {}
        st.session_state["ethics_started"] = True
        st.session_state["ethics_ai_generated"] = use_ai
        st.rerun()
    
    # Display questions if started
    if st.session_state.get("ethics_started"):
        questions = st.session_state.get("ethics_questions", [])
        ai_generated = st.session_state.get("ethics_ai_generated", False)
        
        st.markdown(f"### Responde las siguientes {len(questions)} afirmaciones")
        
        if ai_generated:
            st.success("🤖 **Preguntas generadas con IA** - Estas afirmaciones fueron creadas específicamente para ti usando inteligencia artificial.")
        
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
        # Guardar respuestas en BD (solo una vez)
        if not st.session_state.get("ethics_saved", False):
            try:
                from core.generators.ethics_generator import evaluate_ethics_response, detect_weak_categories
                from db.models import EthicsAttempt
                
                db = SessionLocal()
                user_id = st.session_state.get("user_id")
                questions = st.session_state.get("ethics_questions", [])
                answers = st.session_state.get("ethics_answers", {})
                ai_generated = st.session_state.get("ethics_ai_generated", False)
                
                # Guardar cada respuesta
                for i, q in enumerate(questions):
                    if i in answers:
                        # Extraer valor numérico de la respuesta
                        answer_text = answers[i]
                        respuesta_valor = int(answer_text.split(" - ")[0])
                        
                        # Evaluar respuesta
                        es_correcta, respuesta_esperada, explicacion = evaluate_ethics_response(
                            q["categoria"],
                            q["afirmacion"],
                            respuesta_valor
                        )
                        
                        # Crear registro
                        attempt = EthicsAttempt(
                            user_id=user_id,
                            categoria=q["categoria"],
                            afirmacion=q["afirmacion"],
                            respuesta_usuario=respuesta_valor,
                            respuesta_esperada=respuesta_esperada,
                            es_correcta=es_correcta,
                            ai_generated=ai_generated
                        )
                        db.add(attempt)
                
                db.commit()
                db.close()
                st.session_state["ethics_saved"] = True
                
            except Exception as e:
                st.error(f"Error al guardar respuestas: {e}")
        
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
        
        # Análisis de Debilidades
        st.divider()
        st.subheader("📊 Análisis de Desempeño")
        
        try:
            from core.generators.ethics_generator import detect_weak_categories
            
            db = SessionLocal()
            user_id = st.session_state.get("user_id")
            weak_cats = detect_weak_categories(user_id, db)
            db.close()
            
            if weak_cats:
                st.warning(f"**⚠️ Áreas de mejora detectadas:** {', '.join(weak_cats)}")
                st.info("💡 **Recomendación:** Practica más en estas categorías o usa el generador IA enfocado en tus debilidades.")
            else:
                st.success("✅ ¡Excelente! No se detectaron debilidades significativas en tus respuestas.")
                st.info("💡 Continúa practicando para mantener tu nivel de comprensión del Código de Ética.")
        except Exception as e:
            st.warning(f"No se pudo analizar el desempeño: {e}")
        
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
