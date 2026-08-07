# ruff: noqa: E402
import os
import sys
import time

import pandas as pd
import streamlit as st


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.ai.model_router import ModelRouter
from core.auth import AuthManager
from core.competitions import get_active_competition
from core.learning.session_service import LearningSessionService
from core.learning.tutor import TutorService
from db.models import LearningAttempt, Question
from db.session import SessionLocal
from ui_utils import load_css, render_header


if not AuthManager.check_auth():
    st.warning("Inicia sesión para usar el tutor adaptativo.")
    st.stop()

load_css()
render_header(
    title="Tutor adaptativo",
    subtitle="Una pregunta a la vez, seleccionada según tu progreso real",
)

user_id = st.session_state.get("user_id")
db = SessionLocal()
competition = get_active_competition(db, user_id)
competition_id = competition.id if competition else None
service = LearningSessionService(db)
profile = service.learning_profile(user_id, competition_id)

st.caption(competition.name if competition else "Concurso activo")
metric_cols = st.columns(4)
metric_cols[0].metric("Dominio general", f"{profile['general_mastery']:.0f}%")
metric_cols[1].metric("Tema más débil", profile["weakest_topic"])
metric_cols[2].metric("Revisiones pendientes", profile["due_reviews"])
metric_cols[3].metric("Meta", "Sesión adaptativa")
st.info(profile["recommendation"])

session_id = st.session_state.get("adaptive_learning_session_id")
current = service.get_session(session_id, user_id) if session_id else None
if current and current.status != "active":
    current = None
    st.session_state.pop("adaptive_learning_session_id", None)

if current is None:
    target = st.slider("Duración objetivo", 5, 60, 20, 5, format="%d min")
    if st.button("EMPEZAR SESIÓN", type="primary", use_container_width=True):
        current = service.start_learning_session(
            user_id=user_id,
            target_minutes=target,
            competition_id=competition_id,
        )
        if current.question is None:
            st.error("Este concurso todavía no tiene preguntas disponibles.")
        else:
            st.session_state["adaptive_learning_session_id"] = current.session_id
            st.session_state["adaptive_question_started"] = time.monotonic()
            st.rerun()
else:
    feedback = st.session_state.get("adaptive_feedback")
    if feedback:
        if feedback["result"] == "correct":
            st.success("Correcta")
        elif feedback["result"] == "partial":
            st.warning("Parcialmente correcta")
        else:
            st.error("Incorrecta")
        st.write(feedback["feedback"])
        st.caption(
            f"Dominio del tema: {feedback['mastery']:.1f}% · "
            f"Próximo repaso: {feedback['next_review']}"
        )
        if st.button("Continuar", type="primary", use_container_width=True):
            st.session_state.pop("adaptive_feedback", None)
            st.session_state["adaptive_question_started"] = time.monotonic()
            st.rerun()
    elif current.question:
        question = current.question
        st.progress(0.5, text=f"Tema: {question.topic}")
        st.subheader(question.stem)
        with st.form("adaptive_answer_form"):
            answer = st.radio(
                "Elige una respuesta",
                list(question.options),
                format_func=lambda key: f"{key}. {question.options[key]}",
                index=None,
            )
            confidence = st.radio(
                "¿Qué tan seguro estás?",
                ["low", "medium", "high"],
                format_func={"low": "Baja", "medium": "Media", "high": "Alta"}.get,
                horizontal=True,
                index=1,
            )
            submitted = st.form_submit_button("Responder", type="primary", use_container_width=True)
        if submitted:
            if answer is None:
                st.warning("Selecciona una opción.")
            else:
                elapsed = int(time.monotonic() - st.session_state.get(
                    "adaptive_question_started", time.monotonic()
                ))
                question_row = db.get(Question, question.question_id)
                outcome = service.submit_answer(
                    session_id=current.session_id,
                    user_id=user_id,
                    answer=answer,
                    confidence=confidence,
                    response_time_seconds=max(elapsed, 0),
                )
                evaluation = TutorService(ModelRouter(db_factory=SessionLocal)).explain(
                    stem=question.stem,
                    answer=question.options[answer],
                    deterministic=outcome.evaluation,
                    rationale=question_row.rationale or outcome.evaluation.feedback,
                    confidence=confidence,
                    user_id=user_id,
                )
                st.session_state["adaptive_feedback"] = {
                    "result": evaluation.result.value,
                    "feedback": evaluation.feedback,
                    "mastery": outcome.mastery_score,
                    "next_review": outcome.next_review_at.strftime("%d/%m/%Y %H:%M"),
                }
                st.rerun()
    else:
        st.success("Completaste todas las preguntas disponibles para esta sesión.")

    if st.button("Finalizar sesión", use_container_width=True):
        service.finish_session(current.session_id, user_id)
        st.session_state.pop("adaptive_learning_session_id", None)
        st.session_state.pop("adaptive_feedback", None)
        st.success("Sesión guardada.")
        st.rerun()

with st.expander("Ver progreso", expanded=current is None):
    if not profile["topics"]:
        st.caption("El diagnóstico aparecerá después de tu primera respuesta.")
    else:
        table = pd.DataFrame([
            {
                "Competencia": row.competency or "General",
                "Tema": row.topic_label,
                "Dominio": round(row.mastery_score, 1),
                "Intentos": row.attempts,
                "Próximo repaso": row.next_review_at,
            }
            for row in profile["topics"]
        ])
        competence_tab, topic_tab, evolution_tab = st.tabs(
            ["Competencias", "Temas y repasos", "Evolución reciente"]
        )
        with competence_tab:
            competence_table = table.groupby("Competencia", as_index=False).agg(
                Dominio=("Dominio", "mean"), Intentos=("Intentos", "sum")
            )
            st.dataframe(competence_table, hide_index=True, use_container_width=True)
        with topic_tab:
            st.dataframe(table, hide_index=True, use_container_width=True)
        with evolution_tab:
            recent_query = db.query(LearningAttempt).join(Question).filter(
                LearningAttempt.user_id == user_id
            )
            if competition_id is not None:
                recent_query = recent_query.filter(Question.competition_id == competition_id)
            recent = recent_query.order_by(LearningAttempt.created_at.desc()).limit(30).all()
            if recent:
                evolution = pd.DataFrame([
                    {"Fecha": row.created_at, "Puntaje": row.score * 100}
                    for row in reversed(recent)
                ])
                st.line_chart(evolution, x="Fecha", y="Puntaje")
            else:
                st.caption("Todavía no hay intentos adaptativos para mostrar.")

db.close()
