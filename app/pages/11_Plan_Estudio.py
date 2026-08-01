import datetime
import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.auth import AuthManager
from core.competitions import get_active_competition, get_active_competition_id
from core.study_planner import build_timed_session, days_until_exam, preparation_phase
from db.models import StudyPlanConfig
from db.session import SessionLocal
from ui_utils import load_css, render_custom_sidebar, render_header


DAY_OPTIONS = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

if not AuthManager.check_auth():
    st.warning("Inicia sesión para configurar tu plan de estudio.")
    st.stop()

load_css()
render_custom_sidebar()
render_header(
    title="Plan de estudio",
    subtitle="Configura tu tiempo y deja que el plan se adapte al examen",
)

user_id = st.session_state.get("user_id")
db = SessionLocal()
try:
    competition = get_active_competition(db, user_id)
    competition_id = get_active_competition_id(db, user_id)
    config = db.query(StudyPlanConfig).filter_by(
        user_id=user_id,
        competition_id=competition_id,
    ).first()

    st.info(
        f"Concurso activo: {competition.name if competition else 'Sin concurso configurado'}"
    )

    default_exam_date = config.exam_date if config and config.exam_date else datetime.date(2026, 12, 15)
    default_daily_minutes = config.daily_minutes if config else 30
    default_saturday_minutes = config.saturday_minutes if config else 60
    default_days = config.study_days if config and config.study_days else [0, 1, 2, 3, 4, 5]

    with st.form("study_plan_config_form"):
        exam_date = st.date_input(
            "Fecha estimada del examen",
            value=default_exam_date,
            help="Puedes cambiarla cuando la CNSC publique la fecha oficial.",
        )
        daily_minutes = st.slider(
            "Minutos de lunes a viernes",
            min_value=15,
            max_value=120,
            value=int(default_daily_minutes),
            step=5,
        )
        saturday_minutes = st.slider(
            "Minutos del sábado",
            min_value=15,
            max_value=180,
            value=int(default_saturday_minutes),
            step=15,
        )
        selected_day_names = st.multiselect(
            "Días disponibles",
            list(DAY_OPTIONS.values()),
            default=[DAY_OPTIONS[day] for day in default_days if day in DAY_OPTIONS],
        )
        save = st.form_submit_button("Guardar plan", type="primary", use_container_width=True)

    if save:
        selected_days = [
            day for day, name in DAY_OPTIONS.items() if name in selected_day_names
        ]
        if competition_id is None:
            st.error("Primero configura un concurso y una OPEC activa.")
        elif not selected_days:
            st.error("Selecciona al menos un día de estudio.")
        else:
            if not config:
                config = StudyPlanConfig(
                    user_id=user_id,
                    competition_id=competition_id,
                )
                db.add(config)
            config.exam_date = exam_date
            config.daily_minutes = daily_minutes
            config.saturday_minutes = saturday_minutes
            config.study_days = selected_days
            db.commit()
            st.success("Plan guardado. El Dashboard usará esta disponibilidad.")
            st.rerun()

    preview_minutes = (
        default_saturday_minutes if datetime.date.today().weekday() == 5 else default_daily_minutes
    )
    session = build_timed_session(preview_minutes)
    remaining = days_until_exam(default_exam_date)

    st.subheader("Vista previa de tu sesión")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Tiempo de hoy", f"{session.total_minutes} min")
    metric_cols[1].metric("Días restantes", remaining if remaining is not None else "—")
    metric_cols[2].metric("Etapa", preparation_phase(remaining))

    st.write(
        f"**{session.review_minutes} min** recuperación activa · "
        f"**{session.learning_minutes} min** aprendizaje · "
        f"**{session.practice_minutes} min** práctica "
        f"({session.question_goal} preguntas) · "
        f"**{session.closing_minutes} min** cierre"
    )
finally:
    db.close()