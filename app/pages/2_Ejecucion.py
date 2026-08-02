import streamlit as st
import os, sys, time

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from db.session import SessionLocal
from db.models import Question, Attempt, Skill
import datetime
from core.adaptive import calculate_mastery_update, update_priority
from core.attempt_service import record_attempt
from core.session_results import save_last_result
from core.spaced_repetition import schedule_review
from core.gamification import update_user_stats
from core.rank_system import get_rank_info
from core.exam_format import OFFICIAL_LABEL, official_question_groups, question_format_status
from core.study_resume import (
    clear_daily_run, load_daily_run, restore_daily_run_to_session, save_daily_run, active_elapsed_seconds, pause_daily_run, resume_daily_run, resume_daily_run,
)
from core.generators.llm import LLMGenerator
from core.guided_learning import build_guided_learning_brief
from ui_utils import load_css, render_header, render_favorite_button, escape_html

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
        st.error(f"Ã¢ÂÅ’ Error al guardar resultados: {e}")
        return False

# --- UI Setup ---
if "exam_start_time" not in st.session_state:
    st.session_state["exam_start_time"] = time.time()
    st.session_state["tutor_explanation"] = None
    st.session_state["last_answer_time"] = time.time()

from core.auth import AuthManager

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("SesiÃƒÂ³n expirada. Por favor inicia sesiÃƒÂ³n.")
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
        max-width: 850px !important;
        padding-top: 1rem !important;
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
    st.warning("No hay un examen activo. Ve a 'Nuevo Simulacro'.")
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

render_header(title="SesiÃƒÂ³n diaria guiada" if is_daily_session else "Simulacro en curso")

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
        st.subheader(f"Ã°Å¸â€œâ€“ Estudia durante {brief.get('minutes', 8)} minutos")
        st.markdown(f"### {brief.get('topic', 'Tema de la sesiÃƒÂ³n')}")
        st.caption(f"Macrodominio: {brief.get('macro', 'General')}")
        st.write(f"**Objetivo:** {brief.get('objective', '')}")
        sources = brief.get("sources", [])
        if sources:
            st.markdown("**Consulta estas fuentes:**")
            for source in sources:
                st.markdown(f"- {source}")
        else:
            st.warning(
                "Este bloque no tiene una fuente precisa registrada. No memorices una explicaciÃƒÂ³n "
                "sin respaldo; continÃƒÂºa con la prÃƒÂ¡ctica y revisa la fuente al corregir."
            )
        st.markdown(
            "**RecuperaciÃƒÂ³n activa:** cierra el material y explica en voz alta la regla, "
            "una excepciÃƒÂ³n y cÃƒÂ³mo actuarÃƒÂ­as en un caso laboral."
        )
        ready = st.checkbox(
            "Ya estudiÃƒÂ© la fuente y puedo explicarla sin mirarla",
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
        label = "Ã°Å¸Å¡Â¨ MODO REALISTA (HARDCORE)" if is_hardcore else f"Progreso: {int(progress*100)}%"
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
    st.error("Ã¢ÂÂ³ Ã‚Â¡TIEMPO AGOTADO! Finaliza el examen para guardar tus resultados.")

# Question Card
st.markdown('<div class="dian-card">', unsafe_allow_html=True)
st.caption(f"Eje: {question.track} | Macro: {question.macro_dominio or 'General'}")
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
        "font-weight: 800; margin-bottom: 12px;'>Caso tipo examen Ã‚Â· "
        f"Pregunta {position} de {len(group)}</div>"
        f"<div style='font-size: 1.1rem; line-height: 1.7;'>{escape_html(case.text)}</div></div>",
        unsafe_allow_html=True,
    )

stem_text = question.stem
if "SITUACIÃƒâ€œN:" in stem_text and "PREGUNTA:" in stem_text:
    try:
        parts = stem_text.split("PREGUNTA:")
        sit_part = escape_html(parts[0].replace("SITUACIÃƒâ€œN:", "").strip())
        q_part = escape_html(parts[1].strip())
        st.markdown(f"<div style='background: rgba(230, 0, 0, 0.03); border-left: 6px solid var(--dian-red); padding: 24px; border-radius: 4px 20px 20px 4px; margin-bottom: 24px; backdrop-filter: blur(5px);'><div style='color: var(--dian-red); text-transform: uppercase; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.1em; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;'><span style='background: var(--dian-red); width: 8px; height: 8px; border-radius: 50%;'></span>Caso / SituaciÃƒÂ³n Laboral</div><div style='font-size: 1.1rem; line-height: 1.7; color: #334155;'>{sit_part}</div></div><div class='question-stem'>{q_part}</div>", unsafe_allow_html=True)
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
        "guess": "AdivinÃƒÂ©",
        "unsure": "Tengo dudas",
        "confident": "Estoy seguro",
    }
    selected_confidence = st.radio(
        "Antes de comprobar: Ã‚Â¿quÃƒÂ© tan seguro estÃƒÂ¡s?",
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
st.markdown('</div>', unsafe_allow_html=True) 

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
    if st.button("Ã¢Â¬â€¦Ã¯Â¸Â Anterior", use_container_width=True):
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
                "Ã¢Å“â€¦ Comprobar respuesta", use_container_width=True,
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
                    "desconocimiento": "No conocÃƒÂ­a la regla",
                    "confusion_conceptual": "ConfundÃƒÂ­ conceptos",
                    "mala_interpretacion": "InterpretÃƒÂ© mal el caso",
                    "lectura_incompleta": "No vi una palabra clave",
                    "apuro": "RespondÃƒÂ­ con afÃƒÂ¡n",
                }
                selected_error = st.radio(
                    "Ã‚Â¿CuÃƒÂ¡l fue la causa principal?",
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
            st.info(f"Ã°Å¸â€™Â¡ {question.rationale or 'No hay explicaciÃƒÂ³n disponible.'}")
            if question.source_refs:
                st.caption(f"Ã°Å¸â€œâ€“ Fuente: {question.source_refs}")
    elif not is_hardcore:
        if st.button("Ã°Å¸Â¤â€“ Tutor IA (SocrÃƒÂ¡tico)", use_container_width=True):
            with st.spinner("Analizando..."):
                try:
                    from core.config import get_api_key
                    current_provider = st.session_state.get("current_provider", "Gemini")
                    api_key = get_api_key(current_provider)
                    if api_key:
                        model_name = st.session_state.get("current_model")
                        gen = LLMGenerator(current_provider, api_key, model_name=model_name)
                        q_data = {"stem": question.stem, "options_json": question.options_json, "correct_key": question.correct_key, "rationale": question.rationale}
                        st.session_state["tutor_explanation"] = gen.explain_question(q_data)
                    else: st.warning(f"Ã¢Å¡Â Ã¯Â¸Â API Key de {current_provider} no configurada.")
                except Exception as e: st.error(f"Error: {e}")
    if st.session_state.get("tutor_explanation"):
        st.info(st.session_state["tutor_explanation"])

with col3:
    current_time = time.time()
    time_spent = current_time - st.session_state.get("last_answer_time", current_time)
    if current_idx < total_q - 1:
        if st.button(
            "Siguiente Ã¢Å¾Â¡Ã¯Â¸Â", type="primary", use_container_width=True,
            disabled=is_daily_session and (
                not is_answer_checked
                or (
                    st.session_state["answers"].get(current_q_id) != question.correct_key
                    and current_q_id not in st.session_state["error_types"]
                )
            ),
        ):
            if time_spent < 45 and not is_hardcore:
                st.toast("Ã¢Å¡Â Ã¯Â¸Â EstÃƒÂ¡s respondiendo muy rÃƒÂ¡pido.", icon="Ã¢ÂÂ±Ã¯Â¸Â")
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
        finish_label = "Ã°Å¸ÂÂ Finalizar" if time_left > 0 else "Ã¢Å’â€º Resultados"
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
                st.switch_page("pages/3_Resultados.py")

db.close()








