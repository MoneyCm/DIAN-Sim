"""Biblioteca de estudio trazable para la OPEC activa."""

# ruff: noqa: E402 -- Streamlit ejecuta cada página como script independiente.

from __future__ import annotations

import math
import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.auth import AuthManager
from core.competitions import get_active_competition, get_active_opec
from core.study_library import (
    PROGRESS_LABELS,
    build_study_library,
    load_library_progress,
    save_library_status,
)
from db.session import SessionLocal
from services.question_service import QuestionService
from ui_utils import load_css, render_header


EDITABLE_STATES = ("not_started", "studying", "read", "reviewed")
PAGE_SIZE = 5


if not AuthManager.check_auth():
    st.warning("Inicia sesión para consultar tu biblioteca de estudio.")
    st.stop()

load_css()
render_header(
    title="Qué debo estudiar",
    subtitle="Documentos oficiales vinculados a tu OPEC, con avance y localizadores verificables",
)

user_id = int(st.session_state.get("user_id"))
db = SessionLocal()
try:
    active_opec = get_active_opec(db, user_id)
    competition = get_active_competition(db, user_id)
    if active_opec is None or active_opec.competition_id is None:
        st.warning("Primero selecciona una OPEC en Mis OPEC.")
        st.page_link("pages/14_Mis_OPEC.py", label="Ir a Mis OPEC", icon="🎯")
        st.stop()

    questions = QuestionService.get_questions_for_user(
        db,
        user_id,
        competition_id=active_opec.competition_id,
        user_opec=active_opec,
        bank_partitions=("training",),
    )
    documents = build_study_library(
        active_opec.opec_number,
        question_source_refs=(question.source_refs for question in questions),
    )
    if not documents:
        st.warning(
            "Esta OPEC aún no tiene una biblioteca versionada. El sistema no presentará "
            "documentos genéricos como si fueran un temario oficial."
        )
        st.stop()

    progress = load_library_progress(
        db,
        user_id=user_id,
        competition_id=active_opec.competition_id,
        user_opec_id=active_opec.id,
        opec_number=active_opec.opec_number,
    )
    st.info(
        f"OPEC {active_opec.opec_number} · {active_opec.job_title} · "
        f"{competition.name if competition else 'Concurso asociado'}"
    )
    st.caption(
        "La futura GOA y los ejes definitivos no están publicados. La sección separa la base "
        "oficial del proceso del corpus normativo recomendado por la matriz editorial."
    )

    state_counts = {
        state: sum(progress.get(document.source_id, "not_started") == state for document in documents)
        for state in PROGRESS_LABELS
    }
    metric_cols = st.columns(4)
    metric_cols[0].metric("Documentos vinculados", len(documents))
    metric_cols[1].metric("En estudio", state_counts["studying"])
    metric_cols[2].metric("Leídos o repasados", state_counts["read"] + state_counts["reviewed"])
    metric_cols[3].metric("Preguntas con enlace directo", sum(item.associated_question_count for item in documents))

    filter_cols = st.columns([2, 2, 3])
    priority_filter = filter_cols[0].selectbox(
        "Prioridad", ("Todas", "Alta", "Media", "Baja")
    )
    relation_filter = filter_cols[1].selectbox(
        "Relación",
        ("Todas", "Base oficial", "Corpus recomendado"),
    )
    search = filter_cols[2].text_input(
        "Buscar", placeholder="Documento, tema o función"
    ).strip().lower()

    visible = []
    for document in documents:
        if priority_filter != "Todas" and document.priority != priority_filter:
            continue
        if relation_filter == "Base oficial" and not document.relationship.startswith("Base oficial"):
            continue
        if relation_filter == "Corpus recomendado" and "Corpus oficial" not in document.relationship:
            continue
        haystack = " ".join(
            (
                document.name,
                document.entity,
                " ".join(document.topics),
                " ".join(f"F{number}" for number in document.function_numbers),
            )
        ).lower()
        if search and search not in haystack:
            continue
        visible.append(document)

    page_count = max(1, math.ceil(len(visible) / PAGE_SIZE))
    current_page = min(
        int(st.session_state.get("study_library_page", 1)), page_count
    )
    if page_count > 1:
        current_page = st.select_slider(
            "Página",
            options=list(range(1, page_count + 1)),
            value=current_page,
            format_func=lambda value: f"{value} de {page_count}",
        )
    st.session_state["study_library_page"] = current_page
    page_documents = visible[(current_page - 1) * PAGE_SIZE:current_page * PAGE_SIZE]

    if not page_documents:
        st.info("Ningún documento coincide con los filtros.")
    for document in page_documents:
        current_status = progress.get(document.source_id, "not_started")
        with st.container(border=True):
            title_cols = st.columns([5, 1])
            title_cols[0].markdown(f"### {document.name}")
            title_cols[1].markdown(f"**{document.priority}**")
            st.caption(
                f"{document.entity} · {document.date_version} · Estado: "
                f"{PROGRESS_LABELS[current_status]}"
            )
            st.write(document.relationship)
            if document.function_numbers:
                st.write(
                    "**Funciones relacionadas:** "
                    + ", ".join(f"F{number}" for number in document.function_numbers)
                )
            st.write(f"**Resumen pedagógico:** {document.pedagogical_summary}")
            if document.locator_precise:
                st.write(f"**Localizador:** {document.locator}")
            else:
                st.warning(
                    "El documento está relacionado, pero el artículo/página exacto debe "
                    "confirmarse antes de usarlo para una afirmación normativa."
                )
            st.write(f"**Vigencia registrada:** {document.validity}")
            st.caption(
                f"Consulta de la matriz: {document.consulted_on} · "
                f"Tiempo interno sugerido: {document.estimated_minutes} min · "
                f"Preguntas enlazadas directamente: {document.associated_question_count}"
            )
            st.caption(
                "Regla, excepción y ejemplo laboral: pendientes de curaduría contra el "
                "fragmento oficial; la aplicación no los completa por inferencia."
            )
            if document.url:
                st.link_button("Abrir fuente oficial", document.url)

            if current_status == "mastered":
                st.success(
                    "Dominado con evidencia. Este estado no se asigna por abrir o leer el documento."
                )
            else:
                with st.form(f"library_status_{document.source_id}"):
                    selected_status = st.selectbox(
                        "Mi estado",
                        EDITABLE_STATES,
                        index=EDITABLE_STATES.index(current_status),
                        format_func=lambda value: PROGRESS_LABELS[value],
                    )
                    save = st.form_submit_button("Guardar estado")
                if save:
                    save_library_status(
                        db,
                        user_id=user_id,
                        competition_id=active_opec.competition_id,
                        user_opec_id=active_opec.id,
                        opec_number=active_opec.opec_number,
                        source_id=document.source_id,
                        status=selected_status,
                    )
                    st.rerun()
finally:
    db.close()
