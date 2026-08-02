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
from core.exam_format import LIKERT_OPTIONS
import datetime

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión.")
    st.stop()

load_css()
render_header(
    title="Módulo de Ética e Integridad",
    subtitle="Entrenamiento complementario de juicio ético y valores institucionales",
)

# Load ethics data
ethics_path = os.path.join(PROJECT_ROOT, "data", "codigo_etica_dian.json")
with open(ethics_path, "r", encoding="utf-8") as f:
    ethics_data = json.load(f)

with st.container(border=True):
    st.subheader("📋 Sobre esta práctica")
    st.write(
        "Este módulo entrena decisiones relacionadas con **Ética e Integridad**. "
        "Su formato y ponderación deben confirmarse en la guía oficial del proceso vigente; "
        "los resultados son formativos y no predicen por sí solos el puntaje del examen."
    )
    st.markdown(
        "**Valores institucionales:** Honestidad · Respeto · Compromiso · "
        "Diligencia · Justicia · Transparencia"
    )

st.divider()

# Sidebar info
stats_s, rank = render_custom_sidebar()

# Mode selection
mode = st.radio("Modo de práctica", ["📖 Aprender Código de Ética", "✍️ Práctica de Integridad"], horizontal=True)

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

else:
    # Configuration
    with st.container(border=True):
        st.markdown("**Configura una sesión breve**")
        col1, col2 = st.columns(2)
        with col1:
            categoria = st.selectbox("Categoría",
                ["Todas"] + [s["categoria"] for s in ethics_data["situaciones_eticas_comunes"]])
        with col2:
            num_preguntas = st.select_slider(
                "Duración",
                options=[5, 10, 12, 15, 20, 25, 30],
                value=10,
                format_func=lambda value: f"{value} afirmaciones",
            )
        use_ai = st.toggle(
            "Generar afirmaciones adicionales con IA",
            value=False,
            help="Opcional. El banco estático funciona sin consumir créditos de IA.",
        )
        st.caption("Recomendado: 10 afirmaciones, sin IA, para una práctica breve.")
    
    if st.button("🚀 Iniciar práctica de integridad", type="primary", use_container_width=True):
        for widget_key in [key for key in st.session_state if key.startswith("ethics_q_")]:
            del st.session_state[widget_key]
        all_afirmaciones = []
        
        if use_ai:
            # Generar con IA
            with st.spinner("🤖 Generando afirmaciones éticas con IA..."):
                try:
                    from core.generators.ethics_generator import generate_ethics_statements
                    from core.generators.llm import LLMGenerator
                    from core.config import get_api_key
                    
                    # Obtener API key del usuario
                    provider = "gemini"  # Por defecto
                    api_key = get_api_key(provider)
                    
                    if not api_key:
                        st.error("⚠️ No se encontró API key. Configura tu API key en el Generador IA primero.")
                        st.stop()
                    
                    # En una escala de integridad sin clave correcta no se infieren
                    # debilidades a partir de niveles de acuerdo.
                    weak_categories = []
                    
                    # Crear generador LLM
                    llm_gen = LLMGenerator(provider=provider, api_key=api_key)
                    
                    # Generar afirmaciones
                    if categoria == "Todas":
                        # Generar para todas las categorías proporcionalmente
                        categorias = [s["categoria"] for s in ethics_data["situaciones_eticas_comunes"]]
                        
                        # Distribución uniforme: no hay una clave que justifique
                        # clasificar categorías como fuertes o débiles.
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
        st.session_state["ethics_completed"] = False
        st.session_state["ethics_saved"] = False
        st.rerun()
    
    # Display questions if started
    if st.session_state.get("ethics_started") and not st.session_state.get("ethics_completed"):
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
                options=LIKERT_OPTIONS,
                index=None,
                key=f"ethics_q_{i}",
                horizontal=False,
                on_change=lambda question_index=i: st.session_state["ethics_answers"].update(
                    {question_index: st.session_state.get(f"ethics_q_{question_index}")}
                ),
            )
        
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

                        # La GOA no define clave correcta para esta escala.
                        # Crear registro
                        attempt = EthicsAttempt(
                            user_id=user_id,
                            categoria=q["categoria"],
                            afirmacion=q["afirmacion"],
                            respuesta_usuario=respuesta_valor,
                            respuesta_esperada=None,
                            es_correcta=None,
                            ai_generated=ai_generated
                        )
                        db.add(attempt)
                
                db.commit()
                db.close()
                st.session_state["ethics_saved"] = True
                
            except Exception as e:
                st.error(f"Error al guardar respuestas: {e}")
        
        st.success("✅ Práctica completada")
        st.markdown("### Registro de respuestas")
        
        st.info("""
        **Práctica provisional:** estas afirmaciones no tienen respuestas correctas o incorrectas.
        Sirven para familiarizarte con una escala forzada de cuatro niveles y responder de forma
        honesta y consistente. El formato deberá ajustarse a la guía vigente cuando sea publicada.
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
        
        # Resumen descriptivo, sin convertir niveles de acuerdo en aciertos.
        st.divider()
        st.subheader("📊 Resumen de la práctica")
        answer_values = [
            int(value.split(" - ")[0]) for value in answers.values() if value
        ]
        category_counts = {}
        for item in questions:
            category_counts[item["categoria"]] = category_counts.get(item["categoria"], 0) + 1
        st.metric("Afirmaciones respondidas", len(answer_values))
        st.write("**Cobertura por categoría:**")
        for category_name, count in sorted(category_counts.items()):
            st.write(f"- {category_name}: {count}")
        st.info(
            "Este resumen no asigna puntaje ni diagnostica debilidades. Revisa si comprendiste "
            "cada criterio y si mantuviste una respuesta atenta y coherente."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Nueva práctica"):
                for widget_key in [key for key in st.session_state if key.startswith("ethics_q_")]:
                    del st.session_state[widget_key]
                for key in ["ethics_questions", "ethics_answers", "ethics_started", "ethics_completed", "ethics_saved", "ethics_ai_generated"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        with col2:
            if st.button("📚 Revisar Código de Ética"):
                for widget_key in [key for key in st.session_state if key.startswith("ethics_q_")]:
                    del st.session_state[widget_key]
                for key in ["ethics_questions", "ethics_answers", "ethics_started", "ethics_completed", "ethics_saved", "ethics_ai_generated"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

st.divider()
st.caption("⚖️ **Base formativa:** principios y valores institucionales DIAN. Formato pendiente de confirmación con la guía vigente de la CNSC.")
