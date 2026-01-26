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
from core.gamification import update_user_stats
from core.rank_system import get_rank_info
from core.generators.llm import LLMGenerator
from ui_utils import load_css, render_header

# --- v21: Safe Attribute Assignment Mikey ---
def safe_setattr(obj, attr, value):
    try:
        if hasattr(obj, attr):
            setattr(obj, attr, value)
    except:
        pass

# --- v22: Exam Termination Function ---
def finalize_exam(db, q_ids, answers_dict):
    """Processes all answers and saves to DB."""
    try:
        correct_count = 0
        total_q = len(q_ids)
        u_id = st.session_state.get("user_id")
        eje_results = {} # {"FUNCIONAL": [correct, total], ...}
        
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

            # Create Attempt
            att = Attempt(
                question_id=qid,
                user_id=u_id,
                chosen_key=key_chosen,
                is_correct=is_right,
                created_at=datetime.datetime.utcnow()
            )
            db.add(att)
            
            # Update Records with resilient assignment v21 Mikey
            skill = db.query(Skill).filter_by(user_id=u_id, track=q_obj.track, competency=q_obj.competency, topic=q_obj.topic).first()
            if not skill:
                skill = Skill()
                safe_setattr(skill, "user_id", u_id)
                safe_setattr(skill, "track", q_obj.track)
                safe_setattr(skill, "competency", q_obj.competency)
                safe_setattr(skill, "topic", q_obj.topic)
                safe_setattr(skill, "mastery_score", 0.0)
                safe_setattr(skill, "priority_weight", 1.0)
                db.add(skill)
                db.flush()
            
            # Sync taxonomy & weights safely
            safe_setattr(skill, "macro_dominio", q_obj.macro_dominio)
            safe_setattr(skill, "micro_competencia", q_obj.micro_competencia)
            
            # Update Mastery Record (Fase 2 OPEC)
            from db.models import QuestionPerformance
            perf = db.query(QuestionPerformance).filter_by(user_id=u_id, question_id=qid).first()
            if not perf:
                perf = QuestionPerformance()
                safe_setattr(perf, "user_id", u_id)
                safe_setattr(perf, "question_id", qid)
                safe_setattr(perf, "hits", 0)
                safe_setattr(perf, "misses", 0)
                safe_setattr(perf, "mastery_level", 0.0)
                db.add(perf)
            
            # Safety check for Nulls
            if perf.hits is None: perf.hits = 0
            if perf.misses is None: perf.misses = 0
            
            if is_right:
                perf.hits += 1
            else:
                perf.misses += 1
            
            total_attempts = perf.hits + perf.misses
            if total_attempts > 0:
                safe_setattr(perf, "mastery_level", (perf.hits / total_attempts) * 10.0)
                
            safe_setattr(perf, "last_attempt", datetime.datetime.utcnow())
            
            # Threshold logic v21
            m_lvl = getattr(perf, "mastery_level", 0.0)
            if total_attempts >= 5 and m_lvl >= 7.5:
                safe_setattr(perf, "is_mastered", True)
            
            skill.mastery_score = calculate_mastery_update(is_right, skill.mastery_score)
            
            # Update priority weight safely
            new_weight = update_priority(getattr(skill, "priority_weight", 1.0), is_right)
            safe_setattr(skill, "priority_weight", new_weight)
            
            safe_setattr(skill, "last_seen", datetime.datetime.utcnow())
        
        # Breakdown into dict of tuples for update_user_stats
        breakdown = {k: (v[0], v[1]) for k,v in eje_results.items()}
        
        # Update Gamification with official weighting
        stats, points_earned, new_achievements, rank_up, is_passed = update_user_stats(db, datetime.date.today(), correct_count, total_questions=total_q, eje_breakdown=breakdown, user_id=u_id)
        db.commit()
        
        # Store results for next page
        st.session_state["exam_mode"] = False
        st.session_state["last_results"] = {
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

st.set_page_config(page_title="Simulacro en Curso", page_icon="📝", layout="wide", initial_sidebar_state="collapsed")

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
        max-width: 850px !important;
        padding-top: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

render_header(title="Simulacro en Curso")

if "exam_mode" not in st.session_state or not st.session_state["exam_mode"]:
    st.warning("No hay un examen activo. Ve a 'Nuevo Simulacro'.")
    st.stop()

q_ids = st.session_state["exam_questions"]
current_idx = st.session_state["current_idx"]
total_q = len(q_ids)

db = SessionLocal()
current_q_id = q_ids[current_idx]
question = db.query(Question).filter(Question.question_id == current_q_id).first()

# --- v2.0 NEW: Chronometer / Timer ---
if "total_time_limit" not in st.session_state:
    # GOA Rule: 2.5 minutes per situational question
    st.session_state["total_time_limit"] = 150 * total_q 

# Calculate real-time remaining
elapsed = time.time() - st.session_state.get("exam_start_time", time.time())
time_left = max(0, int(st.session_state["total_time_limit"] - elapsed))

# Hardcore Mode Check
is_hardcore = st.session_state.get("hardcore_mode", False)

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

if time_left <= 0:
    st.error("⏳ ¡TIEMPO AGOTADO! Finaliza el examen para guardar tus resultados.")

# Question Card
st.markdown('<div class="dian-card">', unsafe_allow_html=True)
st.caption(f"Eje: {question.track} | Macro: {question.macro_dominio or 'General'}")
st.markdown(f"### {question.topic}")

stem_text = question.stem
if "SITUACIÓN:" in stem_text and "PREGUNTA:" in stem_text:
    try:
        parts = stem_text.split("PREGUNTA:")
        sit_part = parts[0].replace("SITUACIÓN:", "").strip()
        q_part = parts[1].strip()
        st.markdown(f"<div style='background: rgba(230, 0, 0, 0.03); border-left: 6px solid var(--dian-red); padding: 24px; border-radius: 4px 20px 20px 4px; margin-bottom: 24px; backdrop-filter: blur(5px);'><div style='color: var(--dian-red); text-transform: uppercase; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.1em; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;'><span style='background: var(--dian-red); width: 8px; height: 8px; border-radius: 50%;'></span>Caso / Situación Laboral</div><div style='font-size: 1.1rem; line-height: 1.7; color: #334155;'>{sit_part}</div></div><div class='question-stem'>{q_part}</div>", unsafe_allow_html=True)
    except:
        st.markdown(f"<div class='question-stem'>{stem_text}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='question-stem'>{stem_text}</div>", unsafe_allow_html=True)

options = question.options_json 
opts_keys = list(options.keys())
opts_values = [f"{k}) {v}" for k,v in options.items()]
existing_ans = st.session_state["answers"].get(current_q_id)
index_ans = opts_keys.index(existing_ans) if existing_ans else None
selected_val = st.radio("Selecciona la mejor respuesta:", opts_values, index=index_ans, key=f"q_{current_idx}")
st.markdown('</div>', unsafe_allow_html=True) 

col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    if st.button("⬅️ Anterior", use_container_width=True):
        st.session_state["current_idx"] = max(0, st.session_state["current_idx"] - 1)
        st.session_state["tutor_explanation"] = None
        st.rerun()

with col2:
    if not is_hardcore:
        if st.button("🤖 Tutor IA (Socrático)", use_container_width=True):
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
                    else: st.warning(f"⚠️ API Key de {current_provider} no configurada.")
                except Exception as e: st.error(f"Error: {e}")
    if st.session_state.get("tutor_explanation"):
        st.info(st.session_state["tutor_explanation"])

with col3:
    current_time = time.time()
    time_spent = current_time - st.session_state.get("last_answer_time", current_time)
    if selected_val:
        st.session_state["answers"][current_q_id] = selected_val.split(")")[0]
    if current_idx < total_q - 1:
        if st.button("Siguiente ➡️", type="primary", use_container_width=True):
            if time_spent < 45 and not is_hardcore:
                st.toast("⚠️ Estás respondiendo muy rápido.", icon="⏱️")
            st.session_state["current_idx"] += 1
            st.session_state["last_answer_time"] = time.time()
            st.session_state["tutor_explanation"] = None
            st.rerun()
    else:
        finish_label = "🏁 Finalizar" if time_left > 0 else "⌛ Resultados"
        if st.button(finish_label, type="primary", use_container_width=True):
            if finalize_exam(db, q_ids, st.session_state["answers"]):
                db.close()
                st.switch_page("pages/3_Resultados.py")

db.close()
