
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
from ui_utils import load_css as inject_custom_css, render_favorite_button, escape_html
from services.stats_service import StatsService
from core.auth import AuthManager
from core.competitions import get_active_competition, get_active_competition_id
from core.exam_format import build_official_case_blocks, official_question_groups
from core.real_exam import (
    UAPA_COMPETITION_CODE,
    blueprint_for_competition,
    select_balanced_blocks,
)

# --- CONFIGURACIÓN DE PÁGINA ---
# pass # Removed st.set_page_config

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
        height: auto;
        max-height: 60vh;
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
    .stAlert,
    .stInfo,
    .stSuccess,
    .stWarning,
    .stError,
    .stExpander,
    .stMetric,
    .stProgress {
        display: none !important;
    }
    .question-box {
        margin-bottom: 30px;
        padding: 15px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- FOCUS MODE CSS (Modo examen concentrado) ---
st.markdown("""
<style>
    [data-testid="stHeader"] { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .main .block-container {
        max-width: 760px !important;
        padding-top: 0.7rem !important;
    }
    .stButton button {
        border-radius: 10px !important;
    }
    div[data-testid="stColumn"],
    div[data-testid="column"] {
        width: 100% !important;
        flex: 0 0 100% !important;
        max-width: 100% !important;
    }
    .case-text {
        margin-bottom: 1rem !important;
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
        max-height: 62vh !important;
    }
    [data-testid="stRadio"] label {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .main .block-container > div > div {
        gap: 0.6rem !important;
    }
    .timer-box {
        top: 0.5rem !important;
        right: 0.8rem !important;
        position: sticky !important;
        margin-bottom: 0.8rem !important;
        z-index: 11 !important;
    }
    .stAlert,
    .stInfo,
    .stSuccess,
    .stWarning,
    .stError,
    .stExpander,
    .stMetric,
    .stProgress {
        display: none !important;
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
    from core.exam_format import is_official_functional_case

    if not is_official_functional_case(case):
        return False
    questions = getattr(case, "questions", []) or []
    haystack_parts = [case.title, case.text, getattr(case, "topic", "")]
    for question in questions:
        haystack_parts.extend([
            getattr(question, "stem", ""),
            getattr(question, "rationale", ""),
            getattr(question, "topic", ""),
            getattr(question, "competency", ""),
        ])

    haystack = " ".join(_normalize_exam_text(part) for part in haystack_parts if part)
    if not haystack:
        return False

    # El aislamiento por concurso se realiza en la consulta. Aquí solo validamos
    # que el caso tenga contenido y el formato situacional esperado por CNSC.
    return True


def _official_inventory():
    """Return official and review case counts for the active competition."""
    db = next(get_db())
    try:
        competition_id = get_active_competition_id(db, st.session_state.get("user_id"))
        query = db.query(CaseStudy).options(joinedload(CaseStudy.questions))
        if competition_id is not None:
            query = query.filter(CaseStudy.competition_id == competition_id)
        cases = query.all()
        blocks = build_official_case_blocks(cases)
        source_cases_used = sum(1 for case in cases if official_question_groups(case))
        return len(blocks), max(0, len(cases) - source_cases_used)
    finally:
        db.close()


def _active_exam_context(official_case_count=None):
    db = next(get_db())
    try:
        competition = get_active_competition(db, st.session_state.get("user_id"))
        code = getattr(competition, "code", None)
        try:
            blueprint = blueprint_for_competition(
                code, is_pro=AuthManager.is_pro(), official_case_count=official_case_count
            )
        except TypeError:
            blueprint = blueprint_for_competition(code, is_pro=AuthManager.is_pro())
        return competition, blueprint
    finally:
        db.close()

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

    try:
        user_opec = db.query(UserOPEC).filter_by(user_id=user_id, is_active=True).first() if user_id else None
        competition_id = get_active_competition_id(db, user_id)
        query = db.query(CaseStudy).options(joinedload(CaseStudy.questions))
        if competition_id is not None:
            query = query.filter(CaseStudy.competition_id == competition_id)

        blocks = build_official_case_blocks(query.all())
        if not blocks:
            return []

        # Prefer weak topics, while preserving balanced coverage by domain.
        smart_topics = StatsService.get_smart_mix_topics(
            user_id, count=2, competition_id=competition_id
        ) if user_id else []
        competition = get_active_competition(db, user_id)
        try:
            blueprint = blueprint_for_competition(
                getattr(competition, "code", None), is_pro=AuthManager.is_pro(),
                official_case_count=len(blocks),
            )
        except TypeError:
            blueprint = blueprint_for_competition(
                getattr(competition, "code", None), is_pro=AuthManager.is_pro()
            )
        random.shuffle(blocks)
        return select_balanced_blocks(blocks, blueprint.target_cases, smart_topics)
    except Exception as exc:
        print(f"Error loading official GOA blocks: {exc}")
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
    active_competition, _ = _active_exam_context()
    
    # Modo Simulacro
    st.markdown("""
    ### 🎯 Sobre este Simulacro
    Este modo simula las condiciones oficiales del examen para el concurso y cargo activos:
    
    *   **Formato:** Casos Protagónicos (1 Texto → Múltiples Preguntas)
    *   **Tiempo:** Estricto (2 minutos promedio por pregunta)
    *   **Navegación:** No puedes volver a casos anteriores
    *   **Ayudas:** Deshabilitadas durante el examen
    
    **¿Estás listo para probar tu nivel real?**
    """)
    
    official_cases, review_cases = _official_inventory()
    active_competition, exam_blueprint = _active_exam_context(official_cases)
    st.title(f"⏱️ {exam_blueprint.title}")
    target_cases = exam_blueprint.target_cases
    inventory_cols = st.columns(3)
    inventory_cols[0].metric("Casos oficiales", official_cases)
    inventory_cols[1].metric("Meta de casos", target_cases)
    inventory_cols[2].metric("Casos para revisar", review_cases)
    st.progress(min(official_cases / target_cases, 1.0))
    st.markdown(
        f"**Formato programado:** {min(official_cases, target_cases)} casos · "
        f"{min(official_cases, target_cases) * exam_blueprint.questions_per_case} preguntas · "
        f"{min(official_cases, target_cases) * exam_blueprint.questions_per_case * exam_blueprint.minutes_per_question} minutos."
    )
    if official_cases < 2:
        st.warning(
            "El banco oficial aun no tiene suficientes casos para un simulacro completo. "
            "El material anterior se conserva en Practica/Requiere revision."
        )
    is_uapa_exam = getattr(active_competition, "code", None) == UAPA_COMPETITION_CODE
    if not AuthManager.is_pro() and not is_uapa_exam:
        st.info("💡 Como usuario **Free**, tu simulacro será una versión breve (máximo 2 casos).")
        if st.button("🚀 Desbloquear Simulacro Completo (100 Qs) con PRO", use_container_width=True):
            st.session_state["show_paywall"] = True
            st.rerun()
    
    if "exam_score" in st.session_state:
        c, t = st.session_state.exam_score
        pct = (c/t)*100 if t > 0 else 0
        st.success(f"### Resultado Final: {c}/{t} ({pct:.1f}%)")
        st.markdown(f"### Resumen de sesión")
        st.caption(f"Correctas: {c} de {t} preguntas | Puntaje: {pct:.1f}%")
        
        wrong_count = t - c
        st.markdown(f"**Errores:** {wrong_count}")
        if wrong_count == 0:
            st.success("¡Excelente. No hay fallos detectables en este intento.")
        
        if st.button("Ver análisis detallado y recomendaciones", use_container_width=True):
            st.session_state["show_simulacro_analisis"] = True
            st.rerun()
        
        if not st.session_state.get("show_simulacro_analisis", False):
            st.markdown("Puedes continuar al siguiente simulacro y revisar después las áreas de mejora.")
        else:
            st.markdown("### 🧠 Análisis y recomendaciones")
            # --- RECOMENDACIONES DE ESTUDIO DETALLADAS (v7.0) ---
            cases = st.session_state.get("last_exam_cases", [])
            answers = st.session_state.get("last_user_answers", {})
            
            failed_details = {}  # {topic_key: {...}}
            
            for c_idx, case in enumerate(cases):
                if not _case_is_valid_for_dian(case):
                    continue
                for q in case.questions:
                    user_ans = answers.get(q.question_id)
                    if user_ans == q.correct_key:
                        continue
                    # Determinar el tema/micro-competencia más específico
                    topic_name = q.micro_competencia or q.competency or q.topic or "Competencia General"
                    if topic_name.upper().startswith("OPEC") and "-" in topic_name:
                        topic_name = topic_name.split("-")[-1].strip()
                    
                    track_name = q.track or "FUNCIONAL"
                    macro_name = q.macro_dominio or "General"
                    
                    if topic_name not in failed_details:
                        failed_details[topic_name] = {
                            "topic": topic_name,
                            "track": track_name,
                            "macro": macro_name,
                            "refs": set(),
                            "questions": []
                        }
                    
                    # Agregar referencias limpias
                    ref = getattr(q, 'source_refs', None)
                    if ref:
                        ref_str = str(ref).strip()
                        if ref_str.upper() not in ["", "IA", "NONE", "NULL"]:
                            rf_upper = ref_str.upper()
                            if not ("MISTRAL" in rf_upper or "BATCH GEN" in rf_upper or "INICIAL DIAN" in rf_upper):
                                for r in ref_str.split('\n'):
                                    if r.strip():
                                        failed_details[topic_name]["refs"].add(r.strip())
                    # Agregar detalles de la pregunta fallada
                    failed_details[topic_name]["questions"].append({
                        "stem": q.stem,
                        "chosen": user_ans,
                        "correct": q.correct_key,
                        "correct_text": q.options_json.get(q.correct_key) if q.options_json else "",
                        "rationale": q.rationale
                    })
            
            for t_name, detail in failed_details.items():
                track_val = detail["track"].upper()
                track_color = "#E60000" if "FUNCIONAL" in track_val else "#3b82f6" if "COMPORTAMENTAL" in track_val else "#10b981"
                refs_list = list(detail["refs"])
                
                st.markdown(f"**{detail['topic']}** — {detail['macro']} ({detail['track']})")
                if refs_list:
                    st.caption("Fuentes sugeridas: " + " | ".join(refs_list[:3]))
                for q_item in detail["questions"]:
                    stem_display = q_item["stem"]
                    if "PREGUNTA:" in stem_display:
                        try:
                            stem_display = stem_display.split("PREGUNTA:")[1].strip()
                        except: 
                            pass
                    st.markdown(f"- Tú: `{q_item['chosen']}` | Correcta: `{q_item['correct']}`")
                    if q_item["rationale"]:
                        st.caption(q_item["rationale"])
                if st.button(f"Practicar tema '{t_name}'", key=f"reforce_{t_name}", use_container_width=True):
                    st.session_state["practice_recommended_topic"] = t_name
                    st.switch_page("pages/1_Nuevo_Simulacro.py")
            
            if st.button("Ocultar análisis detallado", use_container_width=True):
                st.session_state["show_simulacro_analisis"] = False
                st.rerun()
    
    if st.button("🔴 INICIAR EXAMEN AHORA", type="primary", use_container_width=True, disabled=official_cases == 0):
        # Clear previous review data
        if "last_exam_cases" in st.session_state: del st.session_state.last_exam_cases
        if "last_user_answers" in st.session_state: del st.session_state.last_user_answers
        if "exam_score" in st.session_state: del st.session_state.exam_score
        if "show_simulacro_analisis" in st.session_state:
            del st.session_state.show_simulacro_analisis
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
    time_left_secs = max(0, int(remaining.total_seconds()))
    color = "#e74c3c" if time_left_secs < 60 else "#2e86c1"
    st.markdown(f"""
    <div class="timer-box" id="timer-box-real" style="background-color: {color};">
        <span id="countdown-real">{mins:02d}:{secs:02d}</span>
    </div>
    """, unsafe_allow_html=True)
    
    js_code = f"""
    <script>
    (function() {{
        let secondsLeft = {time_left_secs};
        const parentDoc = window.parent.document;
        
        function clickStreamlitButton(labelText) {{
            const buttons = Array.from(parentDoc.querySelectorAll("button"));
            for (const btn of buttons) {{
                if (btn.innerText && btn.innerText.toUpperCase().includes(labelText.toUpperCase())) {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        }}
        
        if (window.parent.examRealTimerInterval) {{
            clearInterval(window.parent.examRealTimerInterval);
        }}
        
        window.parent.examRealTimerInterval = setInterval(() => {{
            secondsLeft--;
            if (secondsLeft <= 0) {{
                clearInterval(window.parent.examRealTimerInterval);
                const cd = parentDoc.getElementById("countdown-real");
                if (cd) cd.innerText = "00:00";
                
                // Tratar de finalizar el examen o pasar al siguiente caso (lo cual forzará el fin del examen en backend)
                if (!clickStreamlitButton("FINALIZAR EXAMEN")) {{
                    clickStreamlitButton("Siguiente Caso");
                }}
            }} else {{
                const cd = parentDoc.getElementById("countdown-real");
                if (cd) {{
                    const m = Math.floor(secondsLeft / 60);
                    const s = secondsLeft % 60;
                    cd.innerText = (m < 10 ? '0' : '') + m + ":" + (s < 10 ? '0' : '') + s;
                }}
                const box = parentDoc.getElementById("timer-box-real");
                if (secondsLeft < 60) {{
                    if (box) box.style.backgroundColor = "#e74c3c";
                }} else {{
                    if (box) box.style.backgroundColor = "#2e86c1";
                }}
            }}
        }}, 1000);
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)
    
    # 2. Global Progress
    current_idx = st.session_state.current_case_idx
    current_case = st.session_state.exam_cases[current_idx]

    if not _case_is_valid_for_dian(current_case):
        _reset_invalid_exam_state()
        st.warning("Se detecto un caso invalido y fue descartado antes de mostrarlo.")
        st.rerun()
    
    st.markdown(f"<div style='font-weight:700; margin-bottom:0.8rem; color:#475569;'>Caso {current_idx + 1} de {len(st.session_state.exam_cases)}</div>", unsafe_allow_html=True)
    
    # 3. Layout: One flow (text + questions + one action)
    st.markdown(f"### 📄 {current_case.title or 'Situación'}")
    st.markdown(f'<div class="case-text">{escape_html(current_case.text)}</div>', unsafe_allow_html=True)

    st.markdown("### ❓ Preguntas del Caso")
    for i, q in enumerate(current_case.questions):
        st.markdown(f"#### Pregunta {i+1}")
        st.write(q.stem)

        opts = q.options_json
        options_list = list(opts.keys())

        # Key for state
        k = f"q_{q.question_id}"

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

        if sel:
            st.session_state.user_answers[q.question_id] = sel

    is_last = (current_idx == len(st.session_state.exam_cases) - 1)
    if st.button("Siguiente Caso ➡️" if not is_last else "FINALIZAR EXAMEN 🏁", type="primary", use_container_width=True):
        if is_last:
            finish_exam()
        else:
            st.session_state.current_case_idx += 1
            st.rerun()

