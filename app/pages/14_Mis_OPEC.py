"""Personal OPEC selector: the single source of truth for study focus."""

from __future__ import annotations

import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.auth import AuthManager
from core.competition_readiness import inspect_competition
from core.opec_lookup import attach_reusable_opec_to_user, find_reusable_opec
from core.user_opec_management import OPECNotFoundForUser, activate_opec
from db.models import Competition, UserOPEC
from db.session import SessionLocal
from ui_utils import load_css, log_ui_exception, render_header


if not AuthManager.check_auth():
    st.warning("Inicia sesión para administrar tus OPEC.")
    st.stop()

load_css()
render_header(
    title="Mis OPEC",
    subtitle="Elige el cargo que quieres preparar. Solo uno queda activo para tus prácticas y resultados.",
)


def readiness_label(readiness) -> tuple[str, str]:
    if readiness.enabled_question_count >= 100 and readiness.reviewed_practice_case_count >= 10 and not readiness.pending_review_count:
        return "🟢 Lista para estudiar", "Banco y casos disponibles"
    if readiness.enabled_question_count:
        return "🟡 Base disponible", (
            f"{readiness.enabled_question_count} preguntas habilitadas · "
            f"{readiness.pending_review_count} pendientes de revisión"
        )
    return "⚪ Sin banco habilitado", readiness.next_action


user_id = st.session_state.get("user_id")
db = SessionLocal()
try:
    user_opecs = (
        db.query(UserOPEC)
        .filter_by(user_id=user_id)
        .order_by(UserOPEC.is_active.desc(), UserOPEC.updated_at.desc(), UserOPEC.id.desc())
        .all()
    )

    st.subheader("Tus cargos vinculados")
    if not user_opecs:
        st.info("Todavía no tienes una OPEC vinculada. Busca un número para agregar una ficha ya preparada.")
    else:
        for opec in user_opecs:
            competition = db.get(Competition, opec.competition_id)
            readiness = (
                inspect_competition(
                    db,
                    opec.competition_id,
                    opec_number=opec.opec_number,
                )
                if opec.competition_id
                else None
            )
            status, detail = readiness_label(readiness) if readiness else (
                "⚪ Concurso pendiente", "La OPEC todavía no tiene concurso asociado."
            )
            with st.container(border=True):
                title_col, action_col = st.columns([4, 1])
                with title_col:
                    active = " · **ACTIVA**" if opec.is_active else ""
                    st.markdown(f"### OPEC {opec.opec_number}{active}")
                    st.write(f"**{opec.job_title}** · Nivel {opec.level or 'No informado'}")
                    st.caption(f"{competition.name if competition else 'Concurso por confirmar'}")
                    st.write(status)
                    st.caption(detail)
                with action_col:
                    if opec.is_active:
                        st.success("Estudiando")
                    elif st.button("Activar", key=f"activate_opec_{opec.id}", use_container_width=True):
                        try:
                            activate_opec(db, user_id, opec.id)
                            db.commit()
                            st.session_state.pop("opec_onboarding", None)
                            st.success(f"OPEC {opec.opec_number} activada para estudiar.")
                            st.rerun()
                        except OPECNotFoundForUser:
                            db.rollback()
                            st.error("No fue posible activar esta OPEC.")
                with st.expander("Ver propósito y funciones"):
                    if opec.purpose:
                        st.write(opec.purpose)
                    from core.function_coverage import function_display_label
                    for index, function in enumerate(opec.functions or [], start=1):
                        st.write(function_display_label(opec.opec_number, index, function))

    st.divider()
    st.subheader("Agregar una OPEC preparada")
    st.caption("Escribe solo el número. Si la ficha ya está en el catálogo o fue registrada antes, no necesitas pegarla otra vez.")
    search_col, button_col = st.columns([4, 1])
    with search_col:
        number = st.text_input("Número OPEC", placeholder="Ej.: 242699", label_visibility="collapsed")
    with button_col:
        requested = st.button("Buscar", type="primary", use_container_width=True, disabled=not number.strip())

    if requested:
        result = find_reusable_opec(db, number)
        if result is None:
            st.warning("Aún no hay una ficha preparada para esta OPEC. Puedes registrarla desde Configuración OPEC.")
            st.page_link("pages/15_Centro_OPEC.py", label="Ir a Configuración OPEC")
        else:
            st.session_state["my_opec_search_result"] = result

    result = st.session_state.get("my_opec_search_result")
    if result:
        st.success(f"Encontrada: OPEC {result['opec_number']} · {result['job_title']}")
        st.caption(
            f"{result['competition']['name']} · {len(result['functions'])} funciones · "
            f"{result['catalog_status'].replace('_', ' ')}"
        )
        if st.button("Agregar y activar para estudiar", use_container_width=True):
            try:
                attached = attach_reusable_opec_to_user(db, user_id, result)
                db.commit()
                st.session_state.pop("my_opec_search_result", None)
                st.session_state.pop("opec_onboarding", None)
                st.success(f"OPEC {attached.opec_number} agregada y activada.")
                st.rerun()
            except Exception as exc:
                db.rollback()
                log_ui_exception("my_opec.attach", exc)
                st.error("No se pudo vincular la OPEC. Intenta nuevamente.")

    st.caption("Para registrar una ficha nueva desde SIMO o ajustar sus datos, usa Configuración OPEC.")
    st.page_link("pages/15_Centro_OPEC.py", label="Abrir Configuración OPEC")
finally:
    db.close()
