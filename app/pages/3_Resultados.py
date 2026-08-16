import streamlit as st
import os, sys, datetime
from collections import defaultdict
from zoneinfo import ZoneInfo

# Add root to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# The instruction implies adding this block, but it already exists.
# If `import pandas as pd` was intended to be added, it would go here.
# For now, I will assume the instruction was to ensure the existing block is present.

from db.session import SessionLocal
from db.models import Attempt, Question, UserOPEC
from ui_utils import (
    load_css,
    log_ui_exception,
    metric_card,
    render_favorite_button,
    render_header,
)
from core.pdf_utils import generate_exam_pdf, generate_certificate_pdf
from core.competitions import get_active_competition_id
from core.gamification import (
    PRACTICE_FUNCTIONAL_TARGET,
    PRACTICE_SCORING_DISCLOSURE,
    calculate_practice_index,
)
from services.stats_service import StatsService
from services.question_service import QuestionService

from core.auth import AuthManager
from core.session_results import load_last_result, load_result_history


def _training_questions(db, user_id, competition_id, active_opec):
    if active_opec is None:
        return []
    return QuestionService.get_questions_for_user(
        db,
        user_id,
        competition_id=competition_id,
        user_opec=active_opec,
        bank_partitions=("training",),
    )

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión.")
    st.stop()

load_css()
result_preview = st.session_state.get("last_results", {})
_result_db = SessionLocal()
try:
    _user_id = st.session_state.get("user_id")
    _active_opec = _result_db.query(UserOPEC).filter_by(
        user_id=_user_id, is_active=True
    ).first()
    _competition_id = get_active_competition_id(_result_db, _user_id)
    _opec_number = str(_active_opec.opec_number) if _active_opec else None
    if result_preview and (
        result_preview.get("competition_id") != _competition_id
        or str(result_preview.get("opec_number") or "") != str(_opec_number or "")
    ):
        st.session_state.pop("last_results", None)
        result_preview = {}
    if not result_preview:
        result_preview = load_last_result(
            _result_db, _user_id, _competition_id, _opec_number
        ) or {}
        if result_preview:
            st.session_state["last_results"] = result_preview
finally:
    _result_db.close()
is_daily_session = result_preview.get("session_kind") == "daily"
has_recent_result = bool(result_preview)
render_header(
    title=(
        "Resumen del plan diario" if is_daily_session
        else "Resultados del simulacro" if has_recent_result
        else "Resultados y progreso"
    ),
    subtitle=(
        "Lo aprendido hoy y los temas que debes reforzar"
        if is_daily_session else "Análisis de tu desempeño reciente"
    ),
)
# v2.5.1 - Fix PDF Binary

if not result_preview:
    user_id = st.session_state.get("user_id")
    history_db = SessionLocal()
    try:
        active_competition_id = get_active_competition_id(history_db, user_id)
        attempts = history_db.query(Attempt).join(Question).filter(
            Attempt.user_id == user_id,
            Question.competition_id == active_competition_id,
        ).order_by(Attempt.created_at.desc()).all()
        active_opec = history_db.query(UserOPEC).filter_by(
            user_id=user_id, is_active=True
        ).first()
        eligible_ids = {
            question.question_id
            for question in _training_questions(
                history_db, user_id, active_competition_id, active_opec
            )
        }
        attempts = [attempt for attempt in attempts if attempt.question_id in eligible_ids]

        if not attempts:
            st.info(
                "Todavía no hay intentos guardados en este concurso. Completa el plan diario "
                "o una práctica para comenzar tu historial."
            )
        else:
            total_attempts = len(attempts)
            total_correct = sum(1 for item in attempts if item.is_correct)
            overall_accuracy = total_correct / total_attempts * 100
            practiced_questions = len({item.question_id for item in attempts})
            error_count = total_attempts - total_correct
            metric_cols = st.columns(4)
            metric_cols[0].metric("Intentos guardados", total_attempts)
            metric_cols[1].metric("Precisión acumulada", f"{overall_accuracy:.0f}%")
            metric_cols[2].metric("Preguntas practicadas", practiced_questions)
            metric_cols[3].metric("Errores para aprender", error_count)

            bogota = ZoneInfo("America/Bogota")
            daily = defaultdict(lambda: {"correct": 0, "total": 0})
            for item in attempts:
                created_at = item.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=datetime.timezone.utc)
                day = created_at.astimezone(bogota).date()
                daily[day]["total"] += 1
                daily[day]["correct"] += int(bool(item.is_correct))
            recent_days = sorted(daily.items(), reverse=True)[:7]
            st.subheader("📅 Últimos días con actividad")
            history_rows = [{
                "Fecha": day.strftime("%d/%m/%Y"),
                "Preguntas": values["total"],
                "Correctas": values["correct"],
                "Precisión": f"{values['correct'] / values['total'] * 100:.0f}%",
            } for day, values in recent_days]
            st.dataframe(history_rows, hide_index=True, width="stretch")
            st.caption(
                "Este historial permanece aunque cierres sesión o cambies de dispositivo. "
                "El detalle pregunta por pregunta aparece inmediatamente al terminar una sesión."
            )
    finally:
        history_db.close()

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("🎯 Continuar plan diario", type="primary", use_container_width=True):
            st.switch_page("pages/6_Dashboard.py")
    with action_cols[1]:
        if st.button("▶️ Iniciar práctica", use_container_width=True):
            st.switch_page("pages/1_Nuevo_Simulacro.py")
    st.stop()

data = st.session_state["last_results"]
is_daily_session = data.get("session_kind") == "daily"
breakdown = data.get("breakdown", {})
practice_index, calculated_functional_goal = calculate_practice_index(breakdown)
is_passed = data.get("is_passed", calculated_functional_goal)

# Índice interno de entrenamiento. No representa la ponderación oficial de la OPEC.
f_c, f_t = breakdown.get("FUNCIONAL", (0, 0))
f_pct = (f_c / f_t * 100) if f_t > 0 else 0
total_weighted = practice_index

# --- v2.5 CELEBRATION LOGIC ---
if data.get("new_achievements"):
    st.balloons()
    for ach in data["new_achievements"]:
        st.success(f"🏆 ¡LOGRO DESBLOQUEADO: **{ach}**!")

if data.get("rank_up"):
    st.snow()
    st.warning(f"🎉 ¡ASCENSO DE RANGO! Ahora eres: **{data['rank_up']}**")

total = data["total"]
correct = data["correct"]

# Status Message
if is_daily_session:
    daily_precision = (correct / total * 100) if total else 0
    st.progress(1.0, text="Paso 3 de 3 · Cierre y programación del próximo repaso")
    st.success(
        f"✅ Sesión diaria completada: {correct} de {total} respuestas correctas "
        f"({daily_precision:.0f}%). Los errores ya quedaron programados para repaso."
    )
elif not is_passed:
    st.error(
        "Meta de práctica pendiente: el desempeño funcional quedó por debajo "
        f"del {PRACTICE_FUNCTIONAL_TARGET:.0f}%. Esta etiqueta es de entrenamiento "
        "y no constituye un resultado oficial de la CNSC."
    )
else:
    st.success(
        "Meta de práctica alcanzada en el componente funcional. "
        "Este resultado sirve para orientar el estudio y no equivale a una calificación oficial."
    )

# Metric Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    if is_daily_session:
        metric_card("Precisión de hoy", f"{daily_precision:.0f}%", f"{correct}/{total} correctas")
    else:
        metric_card("Índice de práctica", f"{total_weighted:.1f}/100", f"Funcional: {f_pct:.0f}%")
with col2:
    metric_card("Puntos Ganados", f"+{data.get('points_earned', 0)}", "¡Buen trabajo!")
with col3:
    metric_card("Racha Actual", f"{data.get('new_streak', 0)}🔥", "Días seguidos")
with col4:
    if is_daily_session:
        duration_minutes = max(1, round(int(data.get("duration_seconds", 0)) / 60))
        metric_card("Tiempo activo", f"{duration_minutes} min", "Plan completado")
    else:
        metric_card("Meta funcional", f"{PRACTICE_FUNCTIONAL_TARGET:.0f}%", "Cumplida" if is_passed else "Por reforzar")

if not is_daily_session:
    st.caption(PRACTICE_SCORING_DISCLOSURE)


st.divider()

with st.expander("Historial de sesiones recientes", expanded=False):
    history_db = SessionLocal()
    try:
        session_history = load_result_history(history_db, st.session_state.get("user_id"))
    finally:
        history_db.close()
    if not session_history:
        st.caption("El historial aparecerá después de completar la próxima sesión.")
    else:
        history_rows = []
        for item in reversed(session_history[-10:]):
            item_total = int(item.get("total", 0) or 0)
            item_correct = int(item.get("correct", 0) or 0)
            history_rows.append({
                "Fecha": str(item.get("saved_at", ""))[:16].replace("T", " "),
                "Tipo": "Plan diario" if item.get("session_kind") == "daily" else "Simulacro",
                "Tiempo": f"{max(1, round(int(item.get('duration_seconds', 0) or 0) / 60))} min",
                "Preguntas": item_total,
                "Precisión": f"{(item_correct / item_total * 100):.0f}%" if item_total else "—",
            })
        st.dataframe(history_rows, hide_index=True, use_container_width=True)

# Evidence-based reinforcement summary
st.subheader("🎯 Prioridades de refuerzo")
user_id = st.session_state.get("user_id")
if user_id:
    scope_db = SessionLocal()
    try:
        active_competition_id = get_active_competition_id(scope_db, user_id)
        active_opec = scope_db.query(UserOPEC).filter_by(
            user_id=user_id, is_active=True
        ).first()
        scoped_questions = _training_questions(
            scope_db, user_id, active_competition_id, active_opec
        )
        scoped_question_ids = {item.question_id for item in scoped_questions}
        scoped_topics = {item.topic for item in scoped_questions if item.topic}
    finally:
        scope_db.close()
    weak_skills = StatsService.get_weakest_topics(
        user_id, limit=20, competition_id=active_competition_id
    )
    weak_skills = [item for item in weak_skills if item.topic in scoped_topics][:3]
    
    if weak_skills:
        c_radar, c_recommend = st.columns([1, 1])
        with c_radar:
            st.markdown("##### Temas que conviene reforzar")
            for w in weak_skills:
                st.markdown(f"**{w.topic}** ({w.mastery_score:.0f}%)")
                st.progress(int(max(w.mastery_score, 0)) / 100)
                
        with c_recommend:
            st.markdown("##### 💡 Recomendación inteligente:")
            top_weak = weak_skills[0]
            st.info(f"Deberías reforzar: **{top_weak.topic}**")
            
            # Smart Source Lookup
            try:
                # Find a reference from the bank for this topic
                db_ref = SessionLocal()
                active_opec = db_ref.query(UserOPEC).filter_by(
                    user_id=user_id, is_active=True
                ).first()
                ref_q = next(
                    (
                        item for item in _training_questions(
                            db_ref, user_id, active_competition_id, active_opec
                        )
                        if item.topic == top_weak.topic and item.source_refs
                    ),
                    None,
                )
                if ref_q and ref_q.source_refs:
                    st.markdown(f"> **📖 Lectura prioritaria:**  \n*{ref_q.source_refs}*")
                else:
                    st.markdown("El sistema ha detectado que este es tu punto más débil. Te sugerimos revisar la normativa asociada.")
                db_ref.close()
            except:
                pass
            
            if st.button("▶️ Practicar esta debilidad", key="btn_refuerzo", type="primary"):
                 st.session_state["practice_recommended_topic"] = top_weak.topic
                 st.switch_page("pages/1_Nuevo_Simulacro.py")
    else:
        st.info("Todavía no hay temas evaluados por debajo de la meta en este concurso.")
else:
    st.info("Inicia sesión para ver tu rastreo de debilidades.")

st.divider()

# --- v2.5 PDF DOWNLOAD BUTTON ---
if "show_resultados_detalle" not in st.session_state:
    st.session_state["show_resultados_detalle"] = False

st.subheader("📄 Reporte de desempeño")
db = SessionLocal()
q_ids = data["q_ids"]
answers = st.session_state.get("answers", {})

details = []
active_opec = db.query(UserOPEC).filter_by(
    user_id=st.session_state.get("user_id"), is_active=True
).first()
eligible_detail_ids = {
    item.question_id
    for item in _training_questions(
        db,
        st.session_state.get("user_id"),
        data.get("competition_id"),
        active_opec,
    )
}
for qid in q_ids:
    q = db.query(Question).get(qid)
    if q is None or q.question_id not in eligible_detail_ids:
        continue
    details.append({
        "stem": q.stem,
        "user_ans": answers.get(qid, "N/A"),
        "correct_key": q.correct_key,
        "rationale": q.rationale
    })

if st.button("📋 Ver detalle de respuestas", use_container_width=True, key="toggle_result_detail"):
    st.session_state["show_resultados_detalle"] = True
    st.rerun()

if st.session_state.get("show_resultados_detalle", False):
    # Botones de acción
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("🙈 Ocultar detalle", use_container_width=True):
            st.session_state["show_resultados_detalle"] = False
            st.rerun()
    with col_b2:
        try:
            pdf_bytes = generate_exam_pdf(data, details)
            st.download_button("💾 Reporte PDF", data=pdf_bytes, file_name=f"Resultado_DIAN_{datetime.datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            log_ui_exception("results.pdf.generate", e)
            st.error("No fue posible generar el reporte PDF.")
    with col_b3:
        if is_daily_session:
            st.button("📚 Aprendizaje guardado", disabled=True, use_container_width=True)
        elif total_weighted >= PRACTICE_FUNCTIONAL_TARGET:
            user_name = st.session_state.get("username", "Aspirante")
            from db.models import UserOPEC
            db_o = SessionLocal()
            u_id = st.session_state.get("user_id")
            active_opec = db_o.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
            o_title = active_opec.job_title if active_opec else "Simulacro General"
            db_o.close()
            
            cert_pdf = generate_certificate_pdf(user_name, o_title, total_weighted)
            st.download_button(
                "🎓 Constancia de práctica",
                data=cert_pdf,
                file_name=f"Constancia_practica_{user_name}.pdf",
                mime="application/pdf",
                use_container_width=True,
                help="Documento personal de seguimiento; no es un certificado oficial de la DIAN ni de la CNSC.",
            )
        else:
            st.button(
                f"🎯 Meta interna: {PRACTICE_FUNCTIONAL_TARGET:.0f}%",
                disabled=True,
                use_container_width=True,
                help="Alcanza la meta del índice interno para generar una constancia personal de práctica; no es una certificación oficial.",
            )
else:
    st.caption("Detalle desactivado para foco de estudio. Pulsa el botón para repasar pregunta por pregunta.")

st.divider()

if not is_passed and not is_daily_session:
    st.warning("El reporte PDF se generó, pero la meta interna del componente funcional quedó pendiente.")
    st.info("Te recomendamos una nueva práctica enfocada en las debilidades funcionales detectadas.")
elif st.session_state.get("show_resultados_detalle", False):
    st.subheader("📝 Detalle de respuestas")

    db = SessionLocal()
    q_ids = data["q_ids"]
    answers = st.session_state.get("answers", {})

    for i, qid in enumerate(q_ids):
        q = db.query(Question).get(qid)
        user_ans = answers.get(qid, "N/A")
        is_right = (user_ans == q.correct_key)
        
        icon = "✅" if is_right else "❌"
        color_class = "color: #4CAF50" if is_right else "color: #D90000"
        
        with st.expander(f"{icon} Pregunta {i+1}: {q.topic}"):
            st.markdown(f"<div class='dian-card' style='border:none; padding:0;'>", unsafe_allow_html=True)
            st.markdown(f"**Enunciado:** {q.stem}")
            
            col_ans1, col_ans2 = st.columns(2)
            
            # Get option texts
            opts = q.options_json if q.options_json else {}
            user_text = opts.get(user_ans, "Sin responder")
            correct_text = opts.get(q.correct_key, "")

            with col_ans1:
                st.markdown(f"**Tu respuesta:** <span style='{color_class}; font-weight:bold;'>{user_ans}) {user_text}</span>", unsafe_allow_html=True)
            with col_ans2:
                st.markdown(f"**Correcta:** <span style='color: #4CAF50; font-weight:bold;'>{q.correct_key}) {correct_text}</span>", unsafe_allow_html=True)
            
            st.markdown("---")
            if not is_right:
                st.info(f"💡 **Explicación:** {q.rationale}")
            else:
                st.caption(f"💡 **Explicación:** {q.rationale}")
                
            st.caption(f"ID: {q.question_id} | Macro-Dominio: {q.macro_dominio} | Micro: {q.micro_competencia}")
            render_favorite_button(qid, user_id)
            st.markdown("</div>", unsafe_allow_html=True)

    db.close()

if st.button("🏠 Inicio", type="primary"):
    st.switch_page("pages/6_Dashboard.py")



