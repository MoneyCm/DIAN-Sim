
import streamlit as st
import time
import datetime
import random
import os
import sys
import unicodedata

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.orm import joinedload
from sqlalchemy import func
from db.session import get_db
from db.models import CaseStudy, Question, UserOPEC
from ui_utils import load_css as inject_custom_css, render_favorite_button
from services.stats_service import StatsService
from core.auth import AuthManager

# --- CONFIGURACIÓN DE PÁGINA ---
# st.set_page_config(
    page_title="Simulacro Real - DIAN",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="collapsed" # Real exam usually hides distractions
)

# --- VERIFICACIÓN DE AUTENTICACIÓN ---
if not AuthManager.check_auth():
    st.warning("⚠️ Por favor inicia sesión en la página principal para acceder al Simulacro Real.")
    st.info("El Simulacro Real requiere autenticación para guardar tu progreso y resultados.")
    st.stop()

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

BANNED_SIM_REAL_TERMS = [
    "comision nacional del servicio civil",
    "cnsc",
    "constructora horizonte",
    "constructora soluciones sas",
    "alcaldia municipal",
    "alcalde de villaflores",
    "villaflores",
    "san vicente",
    "lpn-2023-054",
    "contratacion publica",
    "obra publica",
    "licitacion publica",
    "ley 80 de 1993",
    "centro de salud de tercer nivel",
    "procuraduria",
    "fiscalia",
    "dumping",
    "sobornos",
    "campana electoral",
    "sipr",
    "horizonte s.a.",
    "horizonte sa",
    "lpn 2023",
]


def _normalize_exam_text(value):
    value = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def _case_is_valid_for_dian(case):
    questions = getattr(case, "questions", []) or []
    haystack_parts = [case.title, case.text, getattr(case, "topic", "")]
    for question in questions:
        haystack_parts.extend([
            getattr(question, "stem", ""),
            getattr(question, "rationale", ""),
            getattr(question, "topic", ""),
            getattr(question, "competency", ""),
        ])

        options = getattr(question, "options_json", None)
        if not isinstance(options, dict) or len(options) != 3:
            return False

    haystack = " ".join(_normalize_exam_text(part) for part in haystack_parts if part)
    if not haystack:
        return False

    if any(term in haystack for term in BANNED_SIM_REAL_TERMS):
        return False

    if "dian" not in haystack:
        return False

    if "gestor iii de fiscalizacion" in haystack and "dian" not in haystack:
        return False

    return True


def _sanitize_exam_session_state():
    active_cases = st.session_state.get("exam_cases", []) or []
    if active_cases and not all(_case_is_valid_for_dian(case) for case in active_cases):
        st.session_state.exam_cases = []
        st.session_state.exam_active = False
        st.session_state.current_case_idx = 0
        st.session_state.user_answers = {}

    review_cases = st.session_state.get("last_exam_cases", []) or []
    if review_cases and not all(_case_is_valid_for_dian(case) for case in review_cases):
        st.session_state.last_exam_cases = []
        st.session_state.last_user_answers = {}
        if "exam_score" in st.session_state:
            del st.session_state.exam_score


_sanitize_exam_session_state()

def _reset_invalid_exam_state():
    st.session_state.exam_cases = []
    st.session_state.exam_active = False
    st.session_state.current_case_idx = 0
    st.session_state.user_answers = {}


def load_exam_cases():
    db = next(get_db())
    user_id = st.session_state.get("user_id")
    
    # v5.0 SMART MIX LOGIC
    # 1. Detectar Nivel del Usuario (OPEC)
    user_level_int = 3 # Default Profesional
    try:
        if user_id:
            user_opec = db.query(UserOPEC).filter_by(user_id=user_id).first()
            if user_opec and user_opec.level:
                lvl = user_opec.level.upper()
                if "ASISTENCIAL" in lvl: user_level_int = 1
                elif "TECNICO" in lvl: user_level_int = 2
                elif "PROFESIONAL" in lvl: user_level_int = 3
                elif "ASESOR" in lvl: user_level_int = 4
                elif "DIRECTIVO" in lvl: user_level_int = 5
    except Exception as e:
        print(f"Error checking user level: {e}")

    smart_topics = []
    if user_id:
        smart_topics = StatsService.get_smart_mix_topics(user_id, count=2) # 2 targeted, 1 random
    
    final_cases = []
    
    try:
        # A. SMART TOPICS (Filtered by Difficulty if possible, but topics are usually level-agnostic)
        if smart_topics:
            for t in smart_topics:
                # Find case with matching topic AND difficulty
                c = db.query(CaseStudy).join(Question).filter(
                    Question.topic == t,
                    Question.difficulty == user_level_int 
                ).first()
                if c and c not in final_cases and _case_is_valid_for_dian(c):
                    final_cases.append(c)
        
        # B. RANDOM FILL (Filtered by Difficulty AND OPEC Topic)
        is_pro = AuthManager.is_pro()
        target_case_count = 3 if is_pro else 2 
        
        # Obtener el tópico de la OPEC activa para filtrar
        active_topic = f"OPEC {user_opec.opec_number}" if user_opec else "OPEC 236769"
        
        needed = target_case_count - len(final_cases)
        if needed > 0:
            # Seleccionar casos que tengan preguntas del nivel correcto Y correspondan a la OPEC activa
            random_cases = db.query(CaseStudy).join(Question).filter(
                Question.difficulty == user_level_int,
                Question.topic.like(f"%{active_topic}%")
            ).group_by(CaseStudy.id).order_by(func.random()).limit(needed * 2).all()
            
            for rc in random_cases:
                if len(final_cases) >= target_case_count: break
                if rc not in final_cases and rc.questions and _case_is_valid_for_dian(rc):
                    final_cases.append(rc)
                    
        return final_cases
    except Exception as e:
        print(f"Error smart mix: {e}")
        return []
    finally:
        db.close()

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
    
    # v4.1 Persistence
    user_id = st.session_state.get("user_id")
    
    for case in st.session_state.exam_cases:
        for q in case.questions:
            user_choice = st.session_state.user_answers.get(q.question_id)
            is_correct = False
            if user_choice == q.correct_key:
                correct += 1
                is_correct = True
            total += 1
            
            # Save Attempt to DB
            if user_id:
                try:
                    StatsService.record_attempt(
                        user_id=user_id,
                        question_id=q.question_id,
                        chosen_key=user_choice if user_choice else "SKIPPED",
                        is_correct=is_correct,
                        time_sec=0 
                    )
                except Exception as e:
                    print(f"Stats Error: {e}")
            
    st.session_state.exam_score = (correct, total)
    # Save for review
    st.session_state.last_exam_cases = st.session_state.exam_cases
    st.session_state.last_user_answers = st.session_state.user_answers
    
    st.session_state.exam_active = False
    st.rerun()

# --- VISTA PRINCIPAL ---

if not st.session_state.exam_active:
    # --- PANTALLA DE INICIO CON PROTOCOLO ---
    st.title("⏱️ Simulacro de Alta Presión - Modo Examen Real")
    
    # Modo Simulacro
    st.markdown("""
    ### 🎯 Sobre este Simulacro
    Este modo simula las condiciones del examen real para cargos de la DIAN:
    
    *   **Formato:** Casos Protagónicos (1 Texto → Múltiples Preguntas)
    *   **Tiempo:** Estricto (2 minutos promedio por pregunta)
    *   **Navegación:** No puedes volver a casos anteriores
    *   **Ayudas:** Deshabilitadas durante el examen
    
    **¿Estás listo para probar tu nivel real?**
    """)
    
    if not AuthManager.is_pro():
        st.info("💡 Como usuario **Free**, tu simulacro será una versión breve (máximo 2 casos).")
        if st.button("🚀 Desbloquear Simulacro Completo (100 Qs) con PRO", use_container_width=True):
            st.session_state["show_paywall"] = True
            st.rerun()
    
    if "exam_score" in st.session_state:
        c, t = st.session_state.exam_score
        pct = (c/t)*100 if t > 0 else 0
        st.success(f"### Resultado Final: {c}/{t} ({pct:.1f}%)")
        
        # --- RECOMENDACIONES DE ESTUDIO (v6.0) ---
        cases = st.session_state.get("last_exam_cases", [])
        answers = st.session_state.get("last_user_answers", {})
        
        # Mapeo: { "Tema Fallado": set("Fuente 1", "Fuente 2") }
        failed_topics_with_refs = {}
        
        for c_idx, case in enumerate(cases):
            if not _case_is_valid_for_dian(case): continue
            for q in case.questions:
                user_ans = answers.get(q.question_id)
                if user_ans != q.correct_key:
                    # v6.1: Intentar sacar un tema descriptivo
                    topic = ""
                    if q.micro_competencia and q.micro_competencia.strip() and q.micro_competencia.lower() != "general":
                        topic = q.micro_competencia
                    elif q.macro_dominio and q.macro_dominio.strip() and q.macro_dominio.lower() != "transversal":
                        topic = q.macro_dominio
                    elif q.competency and q.competency.strip() and q.competency.lower() != "general":
                        topic = q.competency
                    elif q.topic and not q.topic.upper().startswith("OPEC"):
                        topic = q.topic
                        
                    if not topic:
                        if q.topic and "OPEC" in q.topic.upper():
                            topic = f"Competencias Fundamentales ({q.topic.split('-')[-1].strip() if '-' in q.topic else 'General'})"
                        else:
                            topic = "Razonamiento y Lectura Crítica"
                            
                    # v6.2: Almacenar la fuente documental (source_refs)
                    if topic not in failed_topics_with_refs:
                        failed_topics_with_refs[topic] = set()
                        
                    ref = getattr(q, 'source_refs', None)
                    if ref:
                        ref_str = str(ref).strip()
                        # Si es un string válido y no está en la lista negra estricta
                        if ref_str.upper() not in ["", "IA", "NONE", "NULL"]:
                            # Filtro extendido v6.3: Ignorar marcas de agua de los generadores IA
                            rf_upper = ref_str.upper()
                            if "MISTRAL" in rf_upper or "BATCH GEN" in rf_upper or "INICIAL DIAN" in rf_upper:
                                continue # Ignorar por completo esta referencia basurilla
                                
                            # Limpiar refernecias apiladas
                            for r in ref_str.split('\n'):
                                if r.strip():
                                    failed_topics_with_refs[topic].add(r.strip())
                    
        if failed_topics_with_refs:
            failed_list = list(failed_topics_with_refs.keys())
            st.warning("### 🎯 Recomendaciones de Estudio")
            st.markdown("Basado en tus errores en este simulacro, te sugerimos repasar fuertemente:")
            
            for ft, refs in failed_topics_with_refs.items():
                if refs:
                    # Mostrar tema principal y sus referencias
                    refs_str = " | ".join(list(refs)[:3]) # Limitar a max 3 refs para no congestionar
                    st.markdown(f"- **{ft}** *(Documentos sugeridos: {refs_str})*")
                else:
                    st.markdown(f"- **{ft}**")
                
            # Botón de Auto-Generación
            st.write("")
            if st.button("🤖 Autogenerar Casos de Refuerzo (IA)", type="primary", use_container_width=True):
                # Guardamos el primer tema fallado (o una combinación si se quiere)
                st.session_state["ai_reinforcement_topic"] = failed_list[0]
                st.switch_page("pages/4_Generador_IA.py")
        else:
            if t > 0:
                st.balloons()
                st.success("¡Excelente! No tuviste fallos detectables en temas específicos. Estás listo.")

        # --- REVIEW SECTION ---
        st.markdown("### 📝 Revisión de Respuestas")
        with st.expander("Ver Detalles y Retroalimentación", expanded=True):
            cases = st.session_state.get("last_exam_cases", [])
            answers = st.session_state.get("last_user_answers", {})
            
            for c_idx, case in enumerate(cases):
                if not _case_is_valid_for_dian(case):
                    st.session_state.last_exam_cases = []
                    st.session_state.last_user_answers = {}
                    if "exam_score" in st.session_state:
                        del st.session_state.exam_score
                    st.warning("Se oculto un caso invalido almacenado en la sesion.")
                    st.rerun()
                st.markdown(f"#### 📂 Caso {c_idx+1}: {case.title}")
                st.caption(case.text[:150] + "...") # Preview text
                
                for q in case.questions:
                    user_ans = answers.get(q.question_id)
                    is_ok = (user_ans == q.correct_key)
                    icon = "✅" if is_ok else "❌"
                    color = "green" if is_ok else "red"
                    
                    st.markdown(f"**{icon} Pregunta:** {q.stem}")
                    st.markdown(f"**Tu respuesta:** {user_ans} | **Correcta:** {q.correct_key}")
                    
                    if not is_ok:
                        st.markdown(f"Expected: {q.options_json.get(q.correct_key)}")
                    
                    st.info(f"💡 **Explicación:** {q.rationale}")
                    # Fix NameError v5.4
                    user_id = st.session_state.get("user_id")
                    render_favorite_button(q.question_id, user_id)
                    st.divider()
        
        # Cleanup score but keep review data until new exam starts
        # del st.session_state.exam_score # Keep it for display
    
    if st.button("🔴 INICIAR EXAMEN AHORA", type="primary", use_container_width=True):
        # Clear previous review data
        if "last_exam_cases" in st.session_state: del st.session_state.last_exam_cases
        if "last_user_answers" in st.session_state: del st.session_state.last_user_answers
        if "exam_score" in st.session_state: del st.session_state.exam_score
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

    if not _case_is_valid_for_dian(current_case):
        _reset_invalid_exam_state()
        st.warning("Se detecto un caso invalido y fue descartado antes de mostrarlo.")
        st.rerun()
    
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


