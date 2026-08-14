"""Clear entry point for OPEC setup; selection lives in ``Mis OPEC``."""

from __future__ import annotations

import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.auth import AuthManager
from core.competition_readiness import inspect_competition
from db.models import Competition, UserOPEC
from db.session import SessionLocal
from ui_utils import load_css, render_header


if not AuthManager.check_auth():
    st.warning("Inicia sesión para configurar tu preparación.")
    st.stop()

load_css()
render_header(
    title="Configuración OPEC",
    subtitle="Prepara tu material de estudio. La elección del cargo activo se hace en Mis OPEC.",
)

user_id = st.session_state.get("user_id")
db = SessionLocal()
try:
    active_opec = db.query(UserOPEC).filter_by(user_id=user_id, is_active=True).first()
    if active_opec is None:
        st.warning("Todavía no tienes un cargo activo.")
        st.page_link("pages/14_Mis_OPEC.py", label="Ir a Mis OPEC", icon="🎯")
        st.stop()

    competition = db.get(Competition, active_opec.competition_id)
    readiness = inspect_competition(db, active_opec.competition_id) if competition else None

    with st.container(border=True):
        st.caption("CARGO ACTIVO PARA ESTUDIAR")
        st.subheader(f"OPEC {active_opec.opec_number} · {active_opec.job_title}")
        st.write(competition.name if competition else "Concurso por confirmar")
        if readiness:
            col_questions, col_cases, col_pending = st.columns(3)
            col_questions.metric("Habilitadas", readiness.enabled_question_count)
            col_cases.metric("Casos tipo examen", readiness.official_case_count)
            col_pending.metric("Pendientes", readiness.pending_review_count)
        st.page_link("pages/14_Mis_OPEC.py", label="Cambiar OPEC activa", icon="🎯")

    st.subheader("¿Qué quieres hacer?")
    import_col, bank_col = st.columns(2)
    with import_col:
        with st.container(border=True):
            st.markdown("### Agregar o actualizar una ficha")
            st.write("Pega una ficha nueva de SIMO, busca una OPEC ya registrada o registra otro concurso.")
            st.page_link("pages/7_Configuracion_OPEC.py", label="Abrir herramientas de ficha", icon="📋")
    with bank_col:
        with st.container(border=True):
            st.markdown("### Preparar el banco")
            st.write("Consulta fuentes, revisa el estado del banco y ejecuta la generación inicial cuando corresponda.")
            st.page_link("pages/7_Configuracion_OPEC.py", label="Abrir herramientas de banco", icon="🧰")

    st.info(
        "La OPEC activa controla tus prácticas, resultados, plan y tutor. "
        "El concurso técnico que revises en las herramientas no cambia esa selección."
    )
finally:
    db.close()
