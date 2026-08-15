import streamlit as st
import os, sys, time

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from db.session import SessionLocal
from db.models import Question, Attempt, Skill, UserOPEC
import datetime
from core.adaptive import calculate_mastery_update, update_priority
from core.attempt_service import record_attempt
from core.session_results import save_last_result
from core.spaced_repetition import schedule_review
from core.gamification import update_user_stats
from core.rank_system import get_rank_info
from core.exam_format import OFFICIAL_LABEL, official_question_groups, question_format_status
from core.opec_question_context import manual_function_context
from core.study_resume import (
    clear_daily_run, load_daily_run, restore_daily_run_to_session, save_daily_run,
)
try:
    from core.study_resume import active_elapsed_seconds, pause_daily_run, resume_daily_run
except ImportError:
    # Streamlit Cloud puede conservar durante una recarga el módulo anterior.
    def active_elapsed_seconds(payload, now=None):
        if payload.get("paused"):
            return float(payload.get("active_seconds", 0.0))
        return float(payload.get("active_seconds", 0.0)) + max(
            0.0, (now or time.time()) - float(payload.get("last_resumed_at", time.time()))
        )

    def pause_daily_run(payload, now=None):
        paused = dict(payload)
        paused["active_seconds"] = active_elapsed_seconds(paused, now)
        paused["paused"] = True
        return paused

    def resume_daily_run(payload, now=None):
        resumed = dict(payload)
        resumed["last_resumed_at"] = now or time.time()
        resumed["paused"] = False
        return resumed
from core.generators.llm import LLMGenerator
from core.guided_learning import build_guided_learning_brief
from ui_utils import load_css, render_header, render_favorite_button, escape_html
from core.session_recovery import recover_question_ids
from core.socratic_tutor import local_socratic_hint

# --- v21: Safe Attribute Assignment Mikey ---
def safe_setattr(obj, attr, value):
    try:
        if hasattr(obj, attr):
            setattr(obj, attr, value)
    except:
        pass

# --- v22: Exam Termination Function ---
def finalize_exam(db, q_ids, answers_dict, confidences=None, error_types=None):
    """Processes all answers and saves to DB."""
    try:
        correct_count = 0
        total_q = len(q_ids)
        u_id = st.session_state.get("user_id")
        eje_results = {} # {"FUNCIONAL": [correct, total], ...}
        
        confidences = confidences or {}
        error_types = error_types or {}
        for qid in q_ids:
            q_obj = db.query(Question).get(qid)
            key_chosen = answers_dict.get(qid, "NONE")
            
            is_right = (key_chosen == q_obj.correct_key)
            if is_right:
                correct_count += 1
                
            # Track by Eje for weighting
            track = q_obj.track or "FUNCIONAL"
            if track not in eje_results:
                eje_results[track] = [0, 0]
            eje_results[track][1] += 1
            if is_right:
                eje_results[track][0] += 1

            # Registro Ãºnico: historial, rendimiento, dominio y repaso espaciado.
            record_attempt(
                db, user_id=u_id, question=q_obj, chosen_key=key_chosen,
                confidence=confidences.get(qid, "unsure" if is_right else "guess"),
                error_type=error_types.get(qid),
            )
            if is_right:
                safe_setattr(q_obj, "global_hits", getattr(q_obj, "global_hits", 0) + 1)
            else:
                safe_setattr(q_obj, "global_misses", getattr(q_obj, "global_misses", 0) + 1)
        
        # Breakdown into dict of tuples for update_user_stats
        breakdown = {k: (v[0], v[1]) for k,v in eje_results.items()}
        
        # Update Gamification with official weighting
        stats, points_earned, new_achievements, rank_up, is_passed = update_user_stats(db, datetime.date.today(), correct_count, total_questions=total_q, eje_breakdown=breakdown, user_id=u_id)
        if st.session_state.get("study_session_kind") == "daily":
            clear_daily_run(db, u_id)
        db.commit()
        
        # Store results for next page
        st.session_state["exam_mode"] = False
        st.session_state["last_results"] = {
            "session_kind": st.session_state.get("study_session_kind", "simulation"),
            "duration_seconds": int(
                float(st.session_state.get("active_seconds", 0.0))
                + max(
                    0.0,
                    time.time() - float(
                        st.session_state.get("last_resumed_at", st.session_state.get("exam_start_time", time.time()))
                    ),
                )
            ),
            "total": total_q,
            "correct": correct_count,
            "score": (correct_count / total_q) * 100 if total_q > 0 else 0,
            "q_ids": q_ids,
            "points_earned": points_earned,
            "new_streak": stats.current_streak,
            "rank_up": rank_up,
            "is_passed": is_passed,
            "new_achievements": [a.name for a in new_achievements],
            "breakdown": breakdown
        }
        save_last_result(db, u_id, st.session_state["last_results"])
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        st.error(f"❌ Error al guardar resultados: {e}")
        return False

# --- UI Setup ---
if "exam_start_time" not in st.session_state:
    st.session_state["exam_start_time"] = time.time()
    st.session_state["tutor_explanation"] = None
    st.session_state["last_answer_time"] = time.time()

from core.auth import AuthManager

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Sesión expirada. Por favor inicia sesión.")
    st.stop()

load_css()

# --- FOCUS MODE CSS ---
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
    .stButton button,
    .stDownloadButton button {
        border-radius: 10px !important;
    }
    div[data-testid="stColumn"],
    div[data-testid="column"] {
        width: 100% !important;
        flex: 0 0 100% !important;
        max-width: 100% !important;
    }
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .main .block-container > div > div {
        gap: 0.6rem !important;
    }
    .stExpander,
    .stMetric {
        display: none !important;
    }
    .floating-timer {
        position: sticky !important;
        top: 0.5rem !important;
        right: 0.5rem !important;
        margin-bottom: 0.8rem !important;
        z-index: 10 !important;
    }
</style>
""", unsafe_allow_html=True)

if "exam_mode" not in st.session_state or not st.session_state["exam_mode"]:
    resume_db = SessionLocal()

    resumed_run = load_daily_run(resume_db, st.session_state.get("user_id"))
    resume_db.close()
    if resumed_run:
        restore_daily_run_to_session(st.session_state, resumed_run)

if "exam_mode" not in st.session_state or not st.session_state["exam_mode"]:
    if "last_results" in st.session_state:
        results = st.session_state["last_results"]
        pct = results.get("score", 0.0)
        correct = results.get("correct", 0)
        total = results.get("total", 0)
        st.markdown("### Resultado de la sesión")
        st.caption(f"Correctas: {correct} / {total} • Puntaje: {pct:.1f}%")
        if total > 0:
            st.markdown(f"**Errores:** {total - correct}")
        
        if st.button("Ver análisis detallado y recomendaciones", use_container_width=True):
            st.session_state["show_ejecucion_analisis"] = True
            st.rerun()
        
        if not st.session_state.get("show_ejecucion_analisis", False):
            if st.button("Ir a resultados completos", type="primary", use_container_width=True):
                st.switch_page("pages/3_Resultados.py")
        else:
            st.markdown("### 🧠 Detalle de rendimiento")
            breakdown = results.get("breakdown", {})
            for eje, (aciertos, total_eje) in breakdown.items():
                if total_eje > 0:
                    st.markdown(f"- **{eje}**: {aciertos}/{total_eje} ({(aciertos/total_eje)*100:.1f}%)")
            st.caption(f"Puntos ganados: {results.get('points_earned', 0)}")
            st.caption(f"Racha: {results.get('new_streak', 0)}")
            st.caption(f"Pasaste: {'Sí' if results.get('is_passed') else 'No'}")
            if st.button("Ocultar análisis", use_container_width=True):
                st.session_state["show_ejecucion_analisis"] = False
                st.rerun()
            st.markdown("")
            if st.button("Ir a resultados completos", type="primary", use_container_width=True):
                st.switch_page("pages/3_Resultados.py")

    else:
        st.markdown("### No hay un simulacro activo")
        st.caption("El simulacro anterior terminó al actualizar el banco de preguntas.")
        if st.button("Crear un simulacro nuevo", type="primary", use_container_width=True):
            st.switch_page("pages/1_Nuevo_Simulacro.py")
    st.stop()

is_daily_session = st.session_state.get("study_session_kind") == "daily"
st.session_state.setdefault("confidences", {})
st.session_state.setdefault("error_types", {})

def current_daily_payload(question_ids, position):
    return {
        "question_ids": question_ids,
        "answers": st.session_state.get("answers", {}),
        "checked_answers": st.session_state.get("checked_answers", {}),
        "confidences": st.session_state.get("confidences", {}),
        "error_types": st.session_state.get("error_types", {}),
        "current_idx": position,
        "total_time_limit": st.session_state["total_time_limit"],
        "started_at": st.session_state["exam_start_time"],
        "learning_complete": st.session_state.get("daily_learning_complete", False),
        "learning_minutes": st.session_state.get("daily_learning_minutes", 8),
        "active_seconds": st.session_state.get("active_seconds", 0.0),
        "last_resumed_at": st.session_state.get("last_resumed_at", st.session_state["exam_start_time"]),
        "paused": st.session_state.get("daily_run_paused", False),
    }

render_header(title="Sesión diaria guiada" if is_daily_session else "Simulacro en curso")

practice_format_notice = st.session_state.get("practice_format_notice")
if practice_format_notice in {"GOA", "SITUATIONAL_CASES"}:
    st.success(
        "Práctica OPEC con casos situacionales revisados: se priorizan casos completos y funciones explícitas del manual."
    )
elif practice_format_notice == "SITUATIONAL_FALLBACK":
    st.warning(
        "No había suficientes casos situacionales revisados vinculados a la selección. Esta sesión es situacional de respaldo "
        "y no debe interpretarse como una reproducción del examen oficial."
    )

q_ids = st.session_state["exam_questions"]
current_idx = st.session_state["current_idx"]
total_q = len(q_ids)

db = SessionLocal()

if is_daily_session and st.session_state.get("daily_run_paused", False):
    st.info("Sesión pausada. El cronómetro no está contando tiempo.")
    if st.button("▶️ Reanudar sesión", type="primary", use_container_width=True):
        resumed = resume_daily_run(current_daily_payload(st.session_state["exam_questions"], st.session_state["current_idx"]))
        save_daily_run(db, st.session_state.get("user_id"), resumed)
        restore_daily_run_to_session(st.session_state, resumed)
        st.rerun()

current_q_id = q_ids[current_idx]
question = db.query(Question).filter(Question.question_id == current_q_id).first()

# Una sesión puede conservar identificadores que dejaron de existir después de
# actualizar un banco local. Recuperamos el simulacro con las preguntas aún
# válidas en lugar de dejar la pantalla en blanco al intentar renderizar None.
if question is None:
    valid_ids = {
        row[0] for row in db.query(Question.question_id).filter(
            Question.question_id.in_(q_ids)
        ).all()
    }
    recovered_ids, recovered_position = recover_question_ids(q_ids, valid_ids, current_idx)
    if not recovered_ids:
        db.close()
        st.session_state["exam_mode"] = False
        st.session_state.pop("exam_questions", None)
        st.rerun()
    st.session_state["exam_questions"] = recovered_ids
    st.session_state["current_idx"] = recovered_position
    db.close()
    st.rerun()

if is_daily_session and not st.session_state.get("daily_learning_complete", False):
    loaded_questions = db.query(Question).filter(Question.question_id.in_(q_ids)).all()
    question_by_id = {item.question_id: item for item in loaded_questions}
    session_questions = [question_by_id[qid] for qid in q_ids if qid in question_by_id]
    brief = build_guided_learning_brief(
        session_questions,
        st.session_state.get("daily_learning_minutes", 8),
    )
    st.progress(0.15, text="Paso 1 de 3 · Estudio guiado")
    with st.container(border=True):
        st.subheader(f"📖 Estudia durante {brief.get('minutes', 8)} minutos")
        st.markdown(f"### {brief.get('topic', 'Tema de la sesión')}")
        st.caption(f"Macrodominio: {brief.get('macro', 'General')}")
        st.write(f"**Objetivo:** {brief.get('objective', '')}")
        sources = brief.get("sources", [])
        if sources:
            st.markdown("**Consulta estas fuentes:**")
            for source in sources:
                st.markdown(f"- {source}")
        else:
            st.warning(
                "Este bloque no tiene una fuente precisa registrada. No memorices una explicación "
                "sin respaldo; continúa con la práctica y revisa la fuente al corregir."
            )
        st.markdown(
            "**Recuperación activa:** cierra el material y explica en voz alta la regla, "
            "una excepción y cómo actuarías en un caso laboral."
        )
        ready = st.checkbox(
            "Ya estudié la fuente y puedo explicarla sin mirarla",
            key="daily_learning_ready",
        )
        if st.button(
            "Continuar a las preguntas situacionales",
            type="primary",
            use_container_width=True,
            disabled=not ready,
        ):
            st.session_state["daily_learning_complete"] = True
            save_daily_run(
                db, st.session_state.get("user_id"),
                current_daily_payload(q_ids, current_idx),
            )
            st.rerun()
    db.close()
    st.stop()

if is_daily_session:
    st.caption("Paso 2 de 3 · Práctica situacional adaptativa")

# --- v2.0 NEW: Chronometer / Timer ---
if "total_time_limit" not in st.session_state:
    # GOA Rule: 2.5 minutes per situational question
    st.session_state["total_time_limit"] = 150 * total_q 

# Calculate real-time remaining
if is_daily_session:
    elapsed = active_elapsed_seconds(current_daily_payload(q_ids, current_idx))
else:
    now = time.time()
    elapsed = float(st.session_state.get("active_seconds", 0.0)) + max(
        0.0,
        now - float(st.session_state.get("last_resumed_at", st.session_state.get("exam_start_time", now))),
    )
time_left = max(0, int(st.session_state["total_time_limit"] - elapsed))

# Hardcore Mode Check
is_hardcore = st.session_state.get("hardcore_mode", False)
if "checked_answers" not in st.session_state:
    st.session_state["checked_answers"] = {}
is_answer_checked = bool(st.session_state["checked_answers"].get(current_q_id))

# Progress Area
with st.container():
    col_prog1, col_prog2 = st.columns([3, 1])
    with col_prog1:
        progress = (current_idx / total_q)
        label = "🚨 MODO REALISTA (HARDCORE)" if is_hardcore else f"Progreso: {int(progress*100)}%"
        st.progress(progress, text=label)
    with col_prog2:
        color = "#D90000" if time_left < (total_q * 20) else "#ffa500"
        st.markdown(f"""
        <div class="floating-timer" id="timer-container" style='position: fixed; top: 80px; right: 20px; background: white; padding: 10px 20px; border-radius: 12px; border: 2px solid {color}; box-shadow: 0 4px 15px rgba(0,0,0,0.2); z-index: 9999; text-align: center; min-width: 120px;'>
            <span style='font-size:0.7rem; color:#666; font-weight: bold; text-transform: uppercase;'>Tiempo Restante</span><br>
            <div id="countdown" style='font-size:1.8rem; font-weight:800; color:{color}; font-family: monospace;'>{time_left // 60}:{time_left % 60:02d}</div>
        </div>
        """, unsafe_allow_html=True)
        
        js_code = f"""
        <script>
        (function() {{
            let secondsLeft = {time_left};
            const parentDoc = window.parent.document;
            
            function clickStreamlitButton(labelText) {{
                const buttons = Array.from(parentDoc.querySelectorAll("button"));
                for (const btn of buttons) {{
                    if (btn.innerText && btn.innerText.includes(labelText)) {{
                        btn.click();

                    }}
                }}
                return false;
            }}
            
            if (window.parent.examTimerInterval) {{
                clearInterval(window.parent.examTimerInterval);
            }}
            
            window.parent.examTimerInterval = setInterval(() => {{
                secondsLeft--;
                if (secondsLeft <= 0) {{
                    clearInterval(window.parent.examTimerInterval);
                    const cd = parentDoc.getElementById("countdown");
                    if (cd) cd.innerText = "0:00";
                    clickStreamlitButton("Finalizar");
                    clickStreamlitButton("Resultados");
                }} else {{
                    const cd = parentDoc.getElementById("countdown");
                    if (cd) {{
                        const m = Math.floor(secondsLeft / 60);
                        const s = secondsLeft % 60;
                        cd.innerText = m + ":" + (s < 10 ? '0' : '') + s;
                    }}
                    const container = parentDoc.getElementById("timer-container");
                    if (secondsLeft < 60) {{
                        if (container) container.style.borderColor = "#D90000";
                        if (cd) cd.style.color = "#D90000";
                    }}
                }}
            }}, 1000);
        }})();
        </script>
        """
        st.components.v1.html(js_code, height=0, width=0)

if time_left <= 0:
    st.error("⏳ ¡TIEMPO AGOTADO! Finaliza el examen para guardar tus resultados.")

# Question content. Streamlit cannot wrap later widgets by opening an HTML DIV
# in one markdown call and closing it in another; the opening tag rendered as
# an empty styled card and produced a large blank space above the question.
st.caption(f"Eje: {question.track} | Macro: {question.macro_dominio or 'General'}")
active_opec = db.query(UserOPEC).filter_by(
    user_id=st.session_state.get("user_id"), is_active=True
).first()
manual_context = manual_function_context(
    question,
    getattr(active_opec, "opec_number", ""),
    getattr(active_opec, "functions", []),
)
if manual_context:
    st.info(
        f"🎯 Manual OPEC · Función F{manual_context['number']}: {manual_context['text']}"
    )
if question_format_status(question) == OFFICIAL_LABEL:
    st.caption("Caso situacional revisado · Tres preguntas relacionadas")
st.markdown(f"### {question.topic}")

case = getattr(question, "case_study", None)
if case is not None and question_format_status(question) == OFFICIAL_LABEL:
    group = next(
        (
            items for items in official_question_groups(case)
            if question.question_id in {item.question_id for item in items}
        ),
        [],
    )
    position = next(
        (index for index, item in enumerate(group, start=1) if item.question_id == question.question_id),
        1,
    )
    st.markdown(
        "<div style='background: rgba(230, 0, 0, 0.03); border-left: 6px solid "
        "var(--dian-red); padding: 24px; border-radius: 4px 20px 20px 4px; "
        "margin-bottom: 24px;'>"
        "<div style='color: var(--dian-red); text-transform: uppercase; font-size: 0.75rem; "
        "font-weight: 800; margin-bottom: 12px;'>Caso tipo examen · "
        f"Pregunta {position} de {len(group)}</div>"
        f"<div style='font-size: 1.1rem; line-height: 1.7;'>{escape_html(case.text)}</div></div>",
        unsafe_allow_html=True,
    )

stem_text = question.stem
if "SITUACIÓN:" in stem_text and "PREGUNTA:" in stem_text:
    try:
        parts = stem_text.split("PREGUNTA:")
        sit_part = escape_html(parts[0].replace("SITUACIÓN:", "").strip())
        q_part = escape_html(parts[1].strip())
        st.markdown(f"<div style='background: rgba(230, 0, 0, 0.03); border-left: 6px solid var(--dian-red); padding: 24px; border-radius: 4px 20px 20px 4px; margin-bottom: 24px; backdrop-filter: blur(5px);'><div style='color: var(--dian-red); text-transform: uppercase; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.1em; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;'><span style='background: var(--dian-red); width: 8px; height: 8px; border-radius: 50%;'></span>Caso / Situación Laboral</div><div style='font-size: 1.1rem; line-height: 1.7; color: #334155;'>{sit_part}</div></div><div class='question-stem'>{q_part}</div>", unsafe_allow_html=True)
    except:
        st.markdown(f"<div class='question-stem'>{escape_html(stem_text)}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='question-stem'>{escape_html(stem_text)}</div>", unsafe_allow_html=True)

options = question.options_json 
opts_keys = list(options.keys())
opts_values = []
for k, v in options.items():
    # v47.5 Label Cleanup: Avoid repeating 'A) A.' if the text already has it Mikey
    clean_v = str(v).strip()
    if clean_v.startswith(f"{k})") or clean_v.startswith(f"{k}. "):
        opts_values.append(clean_v)
    else:
        opts_values.append(f"{k}) {clean_v}")
existing_ans = st.session_state["answers"].get(current_q_id)
index_ans = opts_keys.index(existing_ans) if existing_ans else None
selected_val = st.radio(
    "Selecciona la mejor respuesta:", opts_values, index=index_ans,
    key=f"q_{current_idx}", disabled=is_daily_session and is_answer_checked,
)
if selected_val and not is_answer_checked:
    st.session_state["answers"][current_q_id] = selected_val.split(")")[0]
    if is_daily_session:
        save_daily_run(db, st.session_state.get("user_id"), current_daily_payload(q_ids, current_idx))
if is_daily_session and not is_answer_checked:
    confidence_labels = {
        "guess": "Adiviné",
        "unsure": "Tengo dudas",
        "confident": "Estoy seguro",
    }
    selected_confidence = st.radio(
        "Antes de comprobar: ¿qué tan seguro estás?",
        list(confidence_labels),
        format_func=confidence_labels.get,
        index=(
            list(confidence_labels).index(st.session_state["confidences"][current_q_id])
            if current_q_id in st.session_state["confidences"] else None
        ),
        key=f"confidence_{current_q_id}",
        horizontal=True,
    )
    if selected_confidence and st.session_state["confidences"].get(current_q_id) != selected_confidence:
        st.session_state["confidences"][current_q_id] = selected_confidence
        save_daily_run(db, st.session_state.get("user_id"), current_daily_payload(q_ids, current_idx))
render_favorite_button(current_q_id, st.session_state.get("user_id"))

if is_daily_session:
    if st.button("⏸️ Pausar y salir", use_container_width=True):
        payload = pause_daily_run(current_daily_payload(q_ids, current_idx))
        save_daily_run(db, st.session_state.get("user_id"), payload)
        st.session_state["daily_run_paused"] = True
        st.session_state["exam_mode"] = False
        db.close()
        st.switch_page("pages/6_Dashboard.py")

col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    if st.button("↩️ Anterior", use_container_width=True):
        st.session_state["current_idx"] = max(0, st.session_state["current_idx"] - 1)
        if is_daily_session:
            save_daily_run(
                db, st.session_state.get("user_id"),
                current_daily_payload(q_ids, st.session_state["current_idx"]),
            )
        st.session_state["tutor_explanation"] = None
        st.rerun()

with col2:
    if is_daily_session:
        if not is_answer_checked:
            if st.button(
                "✅ Comprobar respuesta", use_container_width=True,
                disabled=(
                    current_q_id not in st.session_state["answers"]
                    or current_q_id not in st.session_state["confidences"]
                ),
            ):
                st.session_state["checked_answers"][current_q_id] = True
                save_daily_run(db, st.session_state.get("user_id"), current_daily_payload(q_ids, current_idx))
                st.rerun()
        else:
            chosen_key = st.session_state["answers"].get(current_q_id)
            if chosen_key == question.correct_key:
                st.success("Respuesta correcta.")
            else:
                correct_text = question.options_json.get(question.correct_key, "")
                st.error(
                    f"La respuesta correcta es {question.correct_key}) {correct_text}"
                )
                error_labels = {
                    "desconocimiento": "No conocía la regla",
                    "confusion_conceptual": "Confundí conceptos",
                    "mala_interpretacion": "Interpreté mal el caso",
                    "lectura_incompleta": "No vi una palabra clave",
                    "apuro": "Respondí con afán",
                }
                selected_error = st.radio(
                    "¿Cuál fue la causa principal?",
                    list(error_labels),
                    format_func=error_labels.get,
                    index=(
                        list(error_labels).index(st.session_state["error_types"][current_q_id])
                        if current_q_id in st.session_state["error_types"] else None
                    ),
                    key=f"error_type_{current_q_id}",
                    horizontal=True,
                )
                if selected_error and st.session_state["error_types"].get(current_q_id) != selected_error:
                    st.session_state["error_types"][current_q_id] = selected_error
                    save_daily_run(db, st.session_state.get("user_id"), current_daily_payload(q_ids, current_idx))
            st.info(f"💡 {question.rationale or 'No hay explicación disponible.'}")
            if question.source_refs:
                st.caption(f"📖 Fuente: {question.source_refs}")
    elif not is_hardcore:
        selected_key = st.session_state["answers"].get(current_q_id)
        st.caption("Ayuda opcional: orienta tu razonamiento, no revela la respuesta ni cambia el puntaje.")
        if st.button(
            "🧭 Revisar mi razonamiento",
            use_container_width=True,
            disabled=not selected_key,
        ):
            with st.spinner("Analizando..."):
                selected_text = question.options_json.get(selected_key, "")
                fallback_hint = local_socratic_hint(
                    topic=question.topic,
                    selected_text=selected_text,
                    source=question.source_refs or "",
                )
                try:
                    from core.config import get_api_key
                    current_provider = st.session_state.get("current_provider", "Gemini")
                    api_key = get_api_key(current_provider)
                    if api_key:
                        model_name = st.session_state.get("current_model")
                        gen = LLMGenerator(current_provider, api_key, model_name=model_name)
                        q_data = {
                            "competition": f"{question.topic} · {question.competency}",
                            "stem": question.stem,
                            "options_json": question.options_json,
                            "selected_key": selected_key,
                            "rationale": question.rationale,
                            "source_refs": question.source_refs,
                        }
                        st.session_state["tutor_explanation"] = gen.explain_socratically(q_data)
                    else:
                        st.session_state["tutor_explanation"] = fallback_hint
                except Exception:
                    st.session_state["tutor_explanation"] = fallback_hint
    if st.session_state.get("tutor_explanation"):
        st.markdown("#### Orientación socrática")
        st.markdown(
            f"<div style='padding:16px 18px;border:1px solid #cbd5e1;border-radius:12px;"
            f"background:#f8fafc;line-height:1.65'>{escape_html(st.session_state['tutor_explanation'])}</div>",
            unsafe_allow_html=True,
        )

with col3:
    current_time = time.time()
    time_spent = current_time - st.session_state.get("last_answer_time", current_time)
    if current_idx < total_q - 1:
        if st.button(
            "Siguiente ➡️", type="primary", use_container_width=True,
            disabled=is_daily_session and (
                not is_answer_checked
                or (
                    st.session_state["answers"].get(current_q_id) != question.correct_key
                    and current_q_id not in st.session_state["error_types"]
                )
            ),
        ):
            if time_spent < 45 and not is_hardcore:
                st.toast("⚠️ Estás respondiendo muy rápido.", icon="⏱️")
            st.session_state["current_idx"] += 1
            if is_daily_session:
                save_daily_run(
                    db, st.session_state.get("user_id"),
                    current_daily_payload(q_ids, st.session_state["current_idx"]),
                )
            st.session_state["last_answer_time"] = time.time()
            st.session_state["tutor_explanation"] = None
            st.rerun()
    else:
        finish_label = "🏁 Finalizar" if time_left > 0 else "🔄 Resultados"
        if st.button(
            finish_label, type="primary", use_container_width=True,
            disabled=is_daily_session and (
                not is_answer_checked
                or (
                    st.session_state["answers"].get(current_q_id) != question.correct_key
                    and current_q_id not in st.session_state["error_types"]
                )
            ),
        ):
            if finalize_exam(
                db, q_ids, st.session_state["answers"],
                st.session_state.get("confidences") if is_daily_session else None,
                st.session_state.get("error_types") if is_daily_session else None,
            ):
                db.close()
                if "show_ejecucion_analisis" in st.session_state:
                    st.session_state["show_ejecucion_analisis"] = False
                st.rerun()

db.close()








