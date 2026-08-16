"""Plan diario explicable y aislado por OPEC."""

# ruff: noqa: E402 -- Streamlit ejecuta cada página como script independiente.

from __future__ import annotations

import datetime
import os
import sys

import streamlit as st
from sqlalchemy import inspect

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.auth import AuthManager
from core.competitions import get_active_competition, get_active_opec
from core.learning.evidence_service import utc_now
from core.opec_question_context import function_number_for_question
from core.study_recommendations import (
    INTERNAL_POLICY_VERSION,
    FunctionEvidence,
    build_daily_mission,
)
from db.models import (
    ErrorEpisode,
    OpecLearningEvent,
    OpecStudyPlan,
    OpecTopicState,
    StudyActivity,
)
from db.session import SessionLocal
from services.question_service import QuestionService
from ui_utils import load_css, render_header


DAY_OPTIONS = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}
ACTIVITY_LABELS = {
    "active_recall": "Recuperación activa",
    "directed_reading": "Lectura dirigida",
    "situational_questions": "Preguntas PJS",
    "error_review": "Cuaderno de errores",
    "spaced_review": "Repaso espaciado",
    "simulation": "Medición cronometrada",
}
ACTIVITY_TYPE_MAP = {"pjs_practice": "situational_questions"}


def _phase2_tables_available(db) -> bool:
    inspector = inspect(db.connection())
    return all(
        inspector.has_table(table)
        for table in (
            "opec_study_plans",
            "study_activities",
            "opec_topic_states",
            "opec_learning_events",
            "error_episodes",
        )
    )


def _get_or_create_plan(db, *, user_id: int, active_opec) -> OpecStudyPlan:
    plan = (
        db.query(OpecStudyPlan)
        .filter_by(
            user_id=user_id,
            competition_id=active_opec.competition_id,
            user_opec_id=active_opec.id,
        )
        .first()
    )
    if plan is None:
        plan = OpecStudyPlan(
            user_id=user_id,
            competition_id=active_opec.competition_id,
            user_opec_id=active_opec.id,
            opec_number=str(active_opec.opec_number),
            target_score=85.0,
            exam_date=None,
            weekday_minutes=30,
            saturday_minutes=60,
            study_days=[0, 1, 2, 3, 4, 5],
            policy_version=INTERNAL_POLICY_VERSION,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


def _function_evidence(db, *, user_id: int, active_opec) -> list[FunctionEvidence]:
    questions = QuestionService.get_questions_for_user(
        db,
        user_id,
        competition_id=active_opec.competition_id,
        user_opec=active_opec,
        bank_partitions=("training",),
    )
    question_ids: dict[int, list[str]] = {number: [] for number in range(1, 10)}
    for question in questions:
        number = function_number_for_question(question, active_opec.opec_number)
        if number in question_ids:
            question_ids[number].append(str(question.question_id))

    states = (
        db.query(OpecTopicState)
        .filter_by(
            user_id=user_id,
            competition_id=active_opec.competition_id,
            user_opec_id=active_opec.id,
        )
        .all()
    )
    events = (
        db.query(OpecLearningEvent)
        .filter_by(user_id=user_id)
        .join(OpecLearningEvent.session)
        .filter_by(
            competition_id=active_opec.competition_id,
            user_opec_id=active_opec.id,
        )
        .all()
    )
    event_by_id = {str(event.id): event for event in events}
    now = utc_now()
    episodes = (
        db.query(ErrorEpisode)
        .filter_by(
            user_id=user_id,
            competition_id=active_opec.competition_id,
            user_opec_id=active_opec.id,
        )
        .filter(ErrorEpisode.status.notin_(("overcome", "dismissed")))
        .all()
    )

    result: list[FunctionEvidence] = []
    for number in range(1, 10):
        function_states = [state for state in states if state.function_number == number]
        evidence_total = sum(max(int(state.evidence_count or 0), 0) for state in function_states)
        if evidence_total:
            mastery = sum(
                float(state.mastery_score or 0.0) * max(int(state.evidence_count or 0), 0)
                for state in function_states
            ) / evidence_total
        elif function_states:
            mastery = sum(float(state.mastery_score or 0.0) for state in function_states) / len(function_states)
        else:
            mastery = 0.0
        function_events = [
            event for event in events
            if event.function_number == number and event.is_correct is not None
        ]
        transfer_events = [event for event in function_events if event.novelty == "transfer"]
        retention = (
            sum(bool(event.is_correct) for event in transfer_events) / len(transfer_events)
            if transfer_events
            else None
        )
        due_errors = sum(
            1
            for episode in episodes
            if event_by_id.get(str(episode.learning_event_id)) is not None
            and event_by_id[str(episode.learning_event_id)].function_number == number
            and (episode.next_review_at is None or episode.next_review_at <= now)
        )
        result.append(
            FunctionEvidence(
                function_number=number,
                mastery_score=round(mastery, 2),
                attempts=len(function_events),
                trusted_question_count=len(question_ids[number]),
                due_error_count=due_errors,
                delayed_retention_rate=retention,
                question_ids=tuple(sorted(question_ids[number])),
            )
        )
    return result


def _ensure_today_activities(db, *, plan: OpecStudyPlan, mission, today: datetime.date):
    existing = (
        db.query(StudyActivity)
        .filter_by(plan_id=plan.id, scheduled_date=today)
        .order_by(StudyActivity.created_at.asc())
        .all()
    )
    if existing:
        return existing
    for spec in mission.activities:
        source_locator = None
        if mission.source is not None and mission.source.locator_verified:
            source_locator = mission.source.locator
        db.add(
            StudyActivity(
                plan_id=plan.id,
                scheduled_date=today,
                minutes=max(1, int(spec.minutes)),
                activity_type=ACTIVITY_TYPE_MAP.get(spec.activity_type, spec.activity_type),
                function_number=mission.function_number,
                topic_id=f"F{mission.function_number:02d}",
                topic_label=mission.topic,
                source_document_id=None,
                source_locator=source_locator,
                objective=spec.instruction,
                rationale=mission.reason,
                status="planned",
            )
        )
    db.commit()
    return (
        db.query(StudyActivity)
        .filter_by(plan_id=plan.id, scheduled_date=today)
        .order_by(StudyActivity.created_at.asc())
        .all()
    )


if not AuthManager.check_auth():
    st.warning("Inicia sesión para ver tu plan de estudio.")
    st.stop()

load_css()
render_header(
    title="Mi plan de hoy",
    subtitle="Una misión concreta, explicable y separada para tu OPEC activa",
)

user_id = int(st.session_state.get("user_id"))
today = datetime.date.today()
db = SessionLocal()
try:
    active_opec = get_active_opec(db, user_id)
    competition = get_active_competition(db, user_id)
    if active_opec is None or active_opec.competition_id is None:
        st.warning("Primero selecciona una OPEC en Mis OPEC.")
        st.page_link("pages/14_Mis_OPEC.py", label="Ir a Mis OPEC", icon="🎯")
        st.stop()
    if not _phase2_tables_available(db):
        st.warning(
            "El plan avanzado aún no está habilitado en esta base de datos. "
            "El administrador debe aplicar la migración aditiva de evidencia de aprendizaje."
        )
        st.stop()

    plan = _get_or_create_plan(db, user_id=user_id, active_opec=active_opec)
    st.info(
        f"OPEC activa: {active_opec.opec_number} · {active_opec.job_title} · "
        f"{competition.name if competition else 'Concurso asociado'}"
    )

    with st.expander("Ajustar mi disponibilidad y objetivo", expanded=False):
        with st.form("opec_study_plan_form"):
            target_score = st.slider(
                "Objetivo interno de precisión",
                min_value=70,
                max_value=100,
                value=int(round(plan.target_score or 85)),
                help=(
                    "Es una meta pedagógica editable. No es el puntaje oficial, "
                    "ni predice el resultado del concurso."
                ),
            )
            has_exam_date = st.checkbox(
                "Usar una fecha para organizar el ritmo",
                value=plan.exam_date is not None,
                help="Déjala desactivada mientras la fecha oficial no esté confirmada.",
            )
            proposed_date = st.date_input(
                "Fecha de planificación",
                value=(
                    plan.exam_date
                    if plan.exam_date is not None and plan.exam_date >= today
                    else today + datetime.timedelta(days=120)
                ),
                min_value=today,
                disabled=not has_exam_date,
            )
            weekday_minutes = st.slider(
                "Minutos en días entre semana",
                min_value=15,
                max_value=120,
                value=int(plan.weekday_minutes or 30),
                step=5,
            )
            saturday_minutes = st.slider(
                "Minutos el sábado",
                min_value=15,
                max_value=180,
                value=int(plan.saturday_minutes or 60),
                step=5,
            )
            selected_day_names = st.multiselect(
                "Días de estudio",
                list(DAY_OPTIONS.values()),
                default=[
                    DAY_OPTIONS[day]
                    for day in (plan.study_days or [])
                    if day in DAY_OPTIONS
                ],
            )
            save = st.form_submit_button(
                "Guardar plan de esta OPEC",
                type="primary",
                use_container_width=True,
            )
        if save:
            selected_days = [
                day for day, name in DAY_OPTIONS.items() if name in selected_day_names
            ]
            if not selected_days:
                st.error("Selecciona al menos un día de estudio.")
            else:
                plan.target_score = float(target_score)
                plan.exam_date = proposed_date if has_exam_date else None
                plan.weekday_minutes = int(weekday_minutes)
                plan.saturday_minutes = int(saturday_minutes)
                plan.study_days = selected_days
                plan.policy_version = INTERNAL_POLICY_VERSION
                db.commit()
                st.success("Plan actualizado solo para esta OPEC.")
                st.rerun()

    if today.weekday() not in (plan.study_days or []):
        st.success("Hoy está marcado como descanso. Puedes practicar si lo deseas, sin romper el plan.")
        st.page_link(
            "pages/1_Nuevo_Simulacro.py",
            label="Hacer una práctica opcional",
            icon="📚",
            use_container_width=True,
        )
        st.stop()

    available_minutes = (
        int(plan.saturday_minutes)
        if today.weekday() == 5
        else int(plan.weekday_minutes)
    )
    evidence = _function_evidence(db, user_id=user_id, active_opec=active_opec)
    mission = build_daily_mission(
        opec_number=active_opec.opec_number,
        available_minutes=available_minutes,
        function_evidence=evidence,
        exam_date=plan.exam_date,
        today=today,
        target_score=plan.target_score,
    )
    if mission is None:
        st.warning(
            "Esta OPEC todavía no tiene una matriz de preparación versionada. "
            "Puedes practicar su banco, pero el sistema no inventará una prioridad ni una fuente."
        )
        st.page_link(
            "pages/1_Nuevo_Simulacro.py",
            label="Practicar con el banco disponible",
            icon="📚",
            use_container_width=True,
        )
        st.stop()

    metric_cols = st.columns(4)
    metric_cols[0].metric("Tiempo de hoy", f"{mission.total_minutes} min")
    metric_cols[1].metric("Prioridad", f"F{mission.function_number}")
    metric_cols[2].metric("Preguntas sugeridas", mission.question_goal)
    metric_cols[3].metric("Objetivo interno", f"{mission.target_score:.0f}%")
    st.caption(
        "El objetivo es una regla interna de entrenamiento; no es un corte oficial "
        "ni garantiza un resultado en el concurso."
    )

    st.subheader(f"Misión: F{mission.function_number} · {mission.function_name}")
    st.write(f"**Tema:** {mission.topic}")
    st.write(mission.reason)
    if mission.source is not None:
        if mission.source.locator_verified:
            st.markdown(
                f"**Fuente prioritaria:** [{mission.source.name}]({mission.source.url}) · "
                f"{mission.source.locator}"
            )
        else:
            st.warning(
                f"Fuente candidata: {mission.source.name}. El localizador exacto aún debe "
                "confirmarse en la biblioteca; no se presenta un artículo o página inventados."
            )
    else:
        st.warning("No hay una fuente oficial precisa vinculada todavía a esta función.")

    activities = _ensure_today_activities(db, plan=plan, mission=mission, today=today)
    completed = sum(activity.status == "completed" for activity in activities)
    st.progress(
        completed / max(len(activities), 1),
        text=f"{completed} de {len(activities)} actividades completadas",
    )
    for activity in activities:
        with st.container(border=True):
            label = ACTIVITY_LABELS.get(activity.activity_type, activity.activity_type)
            st.markdown(f"**{label} · {activity.minutes} min**")
            st.write(activity.objective)
            if activity.source_locator:
                st.caption(f"Localizador verificado: {activity.source_locator}")
            if activity.status == "completed":
                st.success("Completada")
            elif activity.status == "deferred":
                st.info("Pasada a otra fecha")
            else:
                action_cols = st.columns(2)
                if action_cols[0].button(
                    "Marcar completada",
                    key=f"complete_activity_{activity.id}",
                    use_container_width=True,
                ):
                    activity.status = "completed"
                    activity.completed_at = utc_now()
                    db.commit()
                    st.rerun()
                if action_cols[1].button(
                    "Pasar a mañana",
                    key=f"defer_activity_{activity.id}",
                    use_container_width=True,
                ):
                    tomorrow = today + datetime.timedelta(days=1)
                    activity.status = "deferred"
                    duplicate = (
                        db.query(StudyActivity)
                        .filter_by(
                            plan_id=plan.id,
                            scheduled_date=tomorrow,
                            objective=activity.objective,
                        )
                        .first()
                    )
                    if duplicate is None:
                        db.add(
                            StudyActivity(
                                plan_id=plan.id,
                                scheduled_date=tomorrow,
                                minutes=activity.minutes,
                                activity_type=activity.activity_type,
                                function_number=activity.function_number,
                                topic_id=activity.topic_id,
                                topic_label=activity.topic_label,
                                source_document_id=activity.source_document_id,
                                source_locator=activity.source_locator,
                                objective=activity.objective,
                                rationale=activity.rationale,
                                status="planned",
                            )
                        )
                    db.commit()
                    st.rerun()

    if st.button("Practicar ahora esta función", type="primary", use_container_width=True):
        st.session_state["opec_function_filter"] = [mission.function_number]
        st.session_state["opec_function_labels"] = []
        st.switch_page("pages/1_Nuevo_Simulacro.py")
finally:
    db.close()
