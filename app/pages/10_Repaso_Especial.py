import datetime
import os
import sys

import streamlit as st
from sqlalchemy import and_, or_

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.adaptive import calculate_mastery_update, update_priority
from core.auth import AuthManager
from core.spaced_repetition import schedule_review
from db.models import Attempt, Question, QuestionPerformance, Skill
from db.session import SessionLocal
from ui_utils import load_css, render_custom_sidebar, render_favorite_button, render_header


CONFIDENCE_OPTIONS = {
    "Adiviné": "guess",
    "Dudé entre opciones": "unsure",
    "Estaba seguro": "confident",
}

ERROR_TYPES = {
    "No conocía la regla": "desconocimiento",
    "Confundí conceptos": "confusion_conceptual",
    "Interpreté mal el caso": "mala_interpretacion",
    "No vi una palabra clave": "lectura_incompleta",
    "Respondí con afán": "apuro",
}


if not AuthManager.check_auth():
    st.warning("Inicia sesión para acceder a tus repasos.")
    st.stop()

load_css()
render_custom_sidebar()
render_header(
    title="Centro de Repaso Inteligente",
    subtitle="Repasa en el momento adecuado y aprende de la causa de cada error",
)

user_id = st.session_state.get("user_id")
now = datetime.datetime.utcnow()

db = SessionLocal()
try:
    due_count = db.query(QuestionPerformance).filter(
        QuestionPerformance.user_id == user_id,
        or_(
            QuestionPerformance.next_review <= now,
            and_(
                QuestionPerformance.next_review.is_(None),
                QuestionPerformance.misses > 0,
            ),
        ),
    ).count()
finally:
    db.close()

review_tab, errors_tab, favorites_tab = st.tabs(
    [f"🧠 Repasos de hoy ({due_count})", "❌ Banco de errores", "⭐ Favoritas"]
)

with review_tab:
    st.markdown("### Cola de repaso espaciado")
    st.caption(
        "Tu respuesta, seguridad y tipo de error determinan cuándo volverás a ver cada pregunta."
    )

    queue_db = SessionLocal()
    try:
        due_rows = queue_db.query(QuestionPerformance).filter(
            QuestionPerformance.user_id == user_id,
            or_(
                QuestionPerformance.next_review <= now,
                and_(
                    QuestionPerformance.next_review.is_(None),
                    QuestionPerformance.misses > 0,
                ),
            ),
        ).order_by(
            QuestionPerformance.next_review.asc(),
            QuestionPerformance.misses.desc(),
        ).limit(20).all()
        review_queue = [row.question_id for row in due_rows]
    finally:
        queue_db.close()

    review_day = datetime.date.today().isoformat()
    if st.session_state.get("native_review_day") != review_day:
        st.session_state["native_review_day"] = review_day
        st.session_state["native_review_completed"] = 0
    if not review_queue:
        st.success("No tienes repasos vencidos. Vuelve mañana o continúa con tu plan diario.")
        if st.button("Ir al Dashboard", type="primary"):
            st.switch_page("pages/6_Dashboard.py")
    else:
        current_question_id = review_queue[0]
        review_db = SessionLocal()
        try:
            question = review_db.get(Question, current_question_id)
            performance = review_db.query(QuestionPerformance).filter_by(
                user_id=user_id,
                question_id=current_question_id,
            ).first()

            if not question or not performance:
                st.rerun()

            completed = int(st.session_state.get("native_review_completed", 0))
            st.progress(completed / 20)
            st.caption(f"Repaso {completed + 1} de hasta 20 · Tema: {question.topic}")
            st.markdown(f"### {question.stem}")

            option_keys = list(question.options_json.keys())
            selected_key = st.radio(
                "Selecciona una respuesta:",
                option_keys,
                format_func=lambda key: f"{key}) {question.options_json[key]}",
                index=None,
                key=f"native_review_answer_{current_question_id}",
            )

            feedback = st.session_state.get("native_review_feedback")
            if feedback is None:
                if st.button(
                    "Comprobar respuesta",
                    type="primary",
                    disabled=selected_key is None,
                    use_container_width=True,
                ):
                    st.session_state["native_review_feedback"] = {
                        "selected_key": selected_key,
                        "is_correct": selected_key == question.correct_key,
                    }
                    st.rerun()
            else:
                is_correct = feedback["is_correct"]
                if is_correct:
                    st.success("Respuesta correcta.")
                else:
                    st.error(
                        f"La respuesta correcta es {question.correct_key}) "
                        f"{question.options_json.get(question.correct_key, '')}"
                    )
                st.info(question.rationale or "Revisa la regla asociada antes de continuar.")

                confidence_label = st.selectbox(
                    "¿Qué tan seguro estabas?",
                    list(CONFIDENCE_OPTIONS.keys()),
                    index=1,
                )
                error_label = None
                if not is_correct:
                    error_label = st.selectbox(
                        "¿Cuál fue la causa principal del error?",
                        list(ERROR_TYPES.keys()),
                    )

                if st.button("Guardar aprendizaje y continuar", type="primary"):
                    review_time = datetime.datetime.utcnow()
                    chosen_key = feedback["selected_key"]
                    review_db.add(
                        Attempt(
                            question_id=question.question_id,
                            user_id=user_id,
                            chosen_key=chosen_key,
                            is_correct=is_correct,
                            created_at=review_time,
                        )
                    )

                    performance.hits = int(performance.hits or 0) + (1 if is_correct else 0)
                    performance.misses = int(performance.misses or 0) + (0 if is_correct else 1)
                    performance.last_attempt = review_time
                    schedule = schedule_review(
                        performance,
                        is_correct=is_correct,
                        confidence=CONFIDENCE_OPTIONS[confidence_label],
                        error_type=ERROR_TYPES.get(error_label) if error_label else None,
                        now=review_time,
                    )

                    skill = review_db.query(Skill).filter_by(
                        user_id=user_id,
                        track=question.track,
                        competency=question.competency,
                        topic=question.topic,
                    ).first()
                    if not skill:
                        skill = Skill(
                            user_id=user_id,
                            track=question.track,
                            competency=question.competency,
                            topic=question.topic,
                            mastery_score=0.0,
                            priority_weight=1.0,
                        )
                        review_db.add(skill)
                    skill.mastery_score = calculate_mastery_update(
                        is_correct, float(skill.mastery_score or 0.0)
                    )
                    skill.priority_weight = update_priority(
                        float(skill.priority_weight or 1.0), is_correct
                    )
                    skill.last_seen = review_time

                    if is_correct:
                        question.global_hits = int(question.global_hits or 0) + 1
                    else:
                        question.global_misses = int(question.global_misses or 0) + 1

                    review_db.commit()
                    st.toast(
                        f"Próximo repaso en {schedule.interval_days:.0f} día(s).",
                        icon="✅",
                    )
                    st.session_state["native_review_completed"] = completed + 1
                    st.session_state.pop("native_review_feedback", None)
                    st.rerun()

            render_favorite_button(question.question_id, user_id)
        finally:
            review_db.close()

with errors_tab:
    st.markdown("### Preguntas con errores registrados")
    errors_db = SessionLocal()
    try:
        error_rows = errors_db.query(QuestionPerformance).filter(
            QuestionPerformance.user_id == user_id,
            QuestionPerformance.misses > 0,
        ).order_by(QuestionPerformance.misses.desc()).limit(50).all()
        if not error_rows:
            st.success("No tienes errores registrados.")
        for row in error_rows:
            question = errors_db.get(Question, row.question_id)
            if question:
                next_text = (
                    row.next_review.strftime("%Y-%m-%d") if row.next_review else "pendiente"
                )
                with st.expander(
                    f"{question.topic} · {row.misses} fallo(s) · próximo: {next_text}"
                ):
                    st.write(question.stem)
                    st.info(question.rationale or "Sin explicación registrada.")
                    if row.last_error_type:
                        st.caption(f"Última causa detectada: {row.last_error_type}")
    finally:
        errors_db.close()

with favorites_tab:
    st.markdown("### Preguntas favoritas")
    favorites_db = SessionLocal()
    try:
        favorite_rows = favorites_db.query(QuestionPerformance).filter(
            QuestionPerformance.user_id == user_id,
            QuestionPerformance.is_favorite.is_(True),
        ).all()
        if not favorite_rows:
            st.info("No has marcado preguntas favoritas.")
        for row in favorite_rows:
            question = favorites_db.get(Question, row.question_id)
            if question:
                with st.expander(question.topic):
                    st.write(question.stem)
                    st.success(
                        f"Correcta: {question.correct_key}) "
                        f"{question.options_json.get(question.correct_key, '')}"
                    )
                    render_favorite_button(question.question_id, user_id)
    finally:
        favorites_db.close()