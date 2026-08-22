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
from core.socratic_tutor import local_socratic_hint
from core.source_evidence import (
    canonical_source_verification,
    has_precise_source_verification,
)
from db.models import Question
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
        socratic_hint = feedback.get("socratic_hint")
        if socratic_hint:
            st.info(socratic_hint)
        rule = feedback.get("rule")
        if rule:
            st.markdown(f"**Regla registrada:** {rule}")
        st.caption(
            "Excepción normativa: no se inventa. Si la ficha editorial no registra una "
            "excepción sustentada, contrástala en la fuente antes de asumirla."
        )
        if feedback.get("source_url"):
            st.markdown(
                f"**Fuente verificada:** [{feedback['source_locator']}]"
                f"({feedback['source_url']})"
            )
        else:
            st.caption(
                "Fuente declarada pendiente de evidencia editorial precisa; la explicación "
                "se muestra como orientación de práctica."
            )
        st.caption(
            "Origen de la explicación: "
            + (
                "IA opcional apoyada en la justificación registrada."
                if feedback.get("origin") == "ai_guidance_grounded_in_registered_rationale"
                else "motor local determinista; no requiere clave de IA."
            )
        )
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
                index=None,
            )
            reasoning = st.text_area(
                "Explica brevemente por qué elegiste esa opción",
                help="Tu razonamiento permite detectar el concepto exacto detrás de un error.",
            )
            submitted = st.form_submit_button("Responder", type="primary", use_container_width=True)
        if submitted:
            if answer is None:
                st.warning("Selecciona una opción.")
            elif confidence is None:
                st.warning("Indica qué tan seguro estás antes de responder.")
            elif len(reasoning.strip()) < 10:
                st.warning("Explica tu razonamiento en al menos una frase breve.")
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
                    user_reasoning=reasoning,
                )
                tutor = TutorService(ModelRouter(db_factory=SessionLocal))
                evaluation = tutor.explain(
                    stem=question.stem,
                    answer=question.options[answer],
                    deterministic=outcome.evaluation,
                    rationale=question_row.rationale or outcome.evaluation.feedback,
                    confidence=confidence,
                    user_id=user_id,
                )
                legacy_source_verification = (
                    (question_row.quality_report or {}).get("source_verification")
                    if question_row and isinstance(question_row.quality_report, dict)
                    else {}
                ) or {}
                canonical_verification = canonical_source_verification(
                    db, question.question_id
                )
                source_verification = (
                    canonical_verification or legacy_source_verification
                )
                precise_source = bool(
                    canonical_verification
                    or (
                        question_row
                        and has_precise_source_verification(question_row)
                    )
                )
                st.session_state["adaptive_feedback"] = {
                    "result": evaluation.result.value,
                    "feedback": evaluation.feedback,
                    "mastery": outcome.mastery_score,
                    "next_review": outcome.next_review_at.strftime("%d/%m/%Y %H:%M"),
                    "origin": tutor.last_origin,
                    "rule": question_row.rationale or outcome.evaluation.feedback,
                    "socratic_hint": local_socratic_hint(
                        topic=question.topic,
                        selected_text=question.options[answer],
                        source=(
                            f"{source_verification.get('locator')} · "
                            f"{source_verification.get('url')}"
                            if precise_source
                            else ""
                        ),
                    ),
                    "source_url": (
                        source_verification.get("url") if precise_source else None
                    ),
                    "source_locator": (
                        source_verification.get("locator") if precise_source else None
                    ),
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
            recent = service.recent_evolution(user_id, competition_id, limit=30)
            if recent:
                evolution = pd.DataFrame([
                    {"Fecha": row["created_at"], "Puntaje": row["score"]}
                    for row in recent
                ])
                st.line_chart(evolution, x="Fecha", y="Puntaje")
            else:
                st.caption("Todavía no hay intentos adaptativos para mostrar.")

db.close()
