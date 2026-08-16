import datetime
import os
import sys
from collections import Counter
from collections.abc import Mapping

import streamlit as st
from sqlalchemy import and_, inspect, or_

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.attempt_service import record_attempt
from core.auth import AuthManager
from core.competitions import get_active_competition_id
from core.error_notebook import ERROR_CATEGORIES, normalize_error_category
from core.learning.evidence_service import refresh_error_episode
from db.models import ErrorEpisode, Question, QuestionPerformance, UserOPEC
from db.session import SessionLocal
from services.question_service import QuestionService
from ui_utils import load_css, render_favorite_button, render_header


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
ERROR_LABELS = {value: label for label, value in ERROR_TYPES.items()}

PHASE2_ERROR_NOTEBOOK_TABLES = (
    "error_episodes",
    "opec_learning_events",
    "opec_learning_sessions",
    "question_revisions",
)

ERROR_EPISODE_STATUS_LABELS = {
    "open": "Abierto",
    "scheduled": "Programado",
    "in_progress": "En refuerzo",
    "transfer_pending": "Esperando transferencia diferida",
    "overcome": "Superado con transferencia diferida",
    "dismissed": "Descartado",
}

REFRESHABLE_ERROR_STATUSES = {
    "open",
    "scheduled",
    "in_progress",
    "transfer_pending",
}


def _canonical_error_notebook_available(session) -> bool:
    """Use the canonical notebook only when its complete persistence set exists."""

    schema = inspect(session.connection())
    return all(schema.has_table(table) for table in PHASE2_ERROR_NOTEBOOK_TABLES)


def _active_user_opec(session, *, user_id: int, competition_id: int):
    """Resolve one active OPEC inside the authenticated user/competition context."""

    return (
        session.query(UserOPEC)
        .filter(
            UserOPEC.user_id == user_id,
            UserOPEC.competition_id == competition_id,
            UserOPEC.is_active.is_(True),
        )
        .order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc())
        .first()
    )


def _canonical_error_query(session, *, user_id: int, competition_id: int, user_opec):
    """Build the strict context query; never infer an OPEC from question text."""

    return session.query(ErrorEpisode).filter(
        ErrorEpisode.user_id == user_id,
        ErrorEpisode.competition_id == competition_id,
        ErrorEpisode.user_opec_id == user_opec.id,
        ErrorEpisode.opec_number == str(user_opec.opec_number),
    )


def _source_reference_text(reference) -> str:
    if not reference:
        return "Sin fuente registrada."
    if not isinstance(reference, Mapping):
        return str(reference)

    parts = []
    declared = reference.get("declared") or reference.get("document")
    if declared:
        parts.append(str(declared))

    verification = reference.get("verification")
    if isinstance(verification, Mapping):
        for key in ("document", "title", "locator", "article"):
            value = verification.get(key)
            if value and str(value) not in parts:
                parts.append(str(value))
        official_url = (
            verification.get("official_url")
            or verification.get("source_url")
            or verification.get("url")
        )
        if official_url:
            parts.append(str(official_url))
    elif verification:
        parts.append(str(verification))

    for key in ("locator", "article", "official_url", "source_url", "url"):
        value = reference.get(key)
        if value and str(value) not in parts:
            parts.append(str(value))
    return " · ".join(parts) if parts else "Fuente registrada sin detalle legible."


def _date_text(value) -> str:
    return value.strftime("%d/%m/%Y %H:%M") if value else "Pendiente de programación"


def _render_legacy_error_bank(
    session,
    *,
    user_id: int,
    competition_id: int,
    eligible_question_ids: set[str],
) -> None:
    st.caption(
        "Vista histórica de compatibilidad: el esquema del cuaderno canónico todavía "
        "no está instalado en esta base de datos."
    )
    error_rows = session.query(QuestionPerformance).join(Question).filter(
        Question.competition_id == competition_id,
        Question.question_id.in_(eligible_question_ids),
        QuestionPerformance.user_id == user_id,
        QuestionPerformance.misses > 0,
    ).order_by(QuestionPerformance.misses.desc()).limit(50).all()
    if not error_rows:
        st.success("No tienes errores registrados.")
        return

    error_causes = Counter(
        row.last_error_type for row in error_rows if row.last_error_type
    )
    if error_causes:
        most_common_code, most_common_count = error_causes.most_common(1)[0]
        st.info(
            f"Causa más repetida: **{ERROR_LABELS.get(most_common_code, most_common_code)}** "
            f"en {most_common_count} pregunta(s)."
        )
    for row in error_rows:
        question = session.get(Question, row.question_id)
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
                    st.caption(
                        "Última causa detectada: "
                        f"{ERROR_LABELS.get(row.last_error_type, row.last_error_type)}"
                    )


def _render_canonical_error_notebook(
    session,
    *,
    user_id: int,
    competition_id: int,
    now: datetime.datetime,
) -> None:
    active_opec = _active_user_opec(
        session,
        user_id=user_id,
        competition_id=competition_id,
    )
    if active_opec is None:
        st.info("Activa una OPEC de este concurso para consultar su cuaderno de errores.")
        return

    scoped_query = _canonical_error_query(
        session,
        user_id=user_id,
        competition_id=competition_id,
        user_opec=active_opec,
    )
    episodes = scoped_query.order_by(
        ErrorEpisode.next_review_at.asc(),
        ErrorEpisode.created_at.desc(),
    ).limit(100).all()

    refresh_failed = False
    changed = False
    for episode in episodes:
        if episode.status not in REFRESHABLE_ERROR_STATUSES:
            continue
        before = (
            episode.status,
            episode.transfer_event_id,
            episode.overcome_at,
            episode.transfer_evidence,
            tuple(episode.reinforcement_question_ids or []),
        )
        try:
            refresh_error_episode(session, episode, now=now)
        except Exception:
            session.rollback()
            refresh_failed = True
            break
        after = (
            episode.status,
            episode.transfer_event_id,
            episode.overcome_at,
            episode.transfer_evidence,
            tuple(episode.reinforcement_question_ids or []),
        )
        changed = changed or before != after

    if refresh_failed:
        st.warning(
            "No fue posible actualizar la evidencia de transferencia ahora. "
            "Los episodios conservan su último estado guardado."
        )
        episodes = scoped_query.order_by(
            ErrorEpisode.next_review_at.asc(),
            ErrorEpisode.created_at.desc(),
        ).limit(100).all()
    elif changed:
        session.commit()
        episodes = scoped_query.order_by(
            ErrorEpisode.next_review_at.asc(),
            ErrorEpisode.created_at.desc(),
        ).limit(100).all()

    st.caption(
        f"OPEC activa: {active_opec.opec_number} · "
        "un error solo se supera con aciertos situacionales nuevos y diferidos."
    )
    if not episodes:
        st.success("No tienes episodios de error en la OPEC activa.")
        return

    pending_count = sum(
        episode.status in REFRESHABLE_ERROR_STATUSES for episode in episodes
    )
    overcome_count = sum(episode.status == "overcome" for episode in episodes)
    summary_cols = st.columns(3)
    summary_cols[0].metric("Episodios", len(episodes))
    summary_cols[1].metric("En aprendizaje", pending_count)
    summary_cols[2].metric("Superados", overcome_count)

    for episode in episodes:
        category_code = normalize_error_category(episode.category)
        category_label = ERROR_CATEGORIES.get(category_code, category_code)
        status_label = ERROR_EPISODE_STATUS_LABELS.get(
            episode.status, episode.status
        )
        question = session.get(Question, episode.question_id)
        topic = question.topic if question else f"Pregunta {episode.question_id}"
        with st.expander(f"{topic} · {category_label} · {status_label}"):
            if question:
                st.write(question.stem)
            st.markdown(f"**Categoría:** {category_label}")
            st.markdown(
                f"**Razón del error:** {episode.failure_reason or 'Sin diagnóstico registrado.'}"
            )
            if episode.user_reasoning:
                st.markdown(f"**Tu razonamiento:** {episode.user_reasoning}")
            st.markdown(
                f"**Regla para recordar:** {episode.rule_to_remember or 'Pendiente de consolidar.'}"
            )
            st.markdown(f"**Fuente:** {_source_reference_text(episode.source_reference)}")
            st.info(
                "**Microlección:** "
                f"{episode.micro_lesson or 'Pendiente de generar a partir de la evidencia.'}"
            )
            st.markdown(f"**Próximo repaso:** {_date_text(episode.next_review_at)}")
            st.markdown(f"**Estado:** {status_label}")
            evidence = episode.transfer_evidence or {}
            if evidence:
                qualifying = int(evidence.get("qualifying_count") or 0)
                required = int(evidence.get("required_count") or 2)
                reason = str(evidence.get("reason") or "").strip()
                evidence_text = f"Transferencias válidas: {qualifying} de {required}."
                if reason:
                    evidence_text = f"{evidence_text} {reason}"
                st.caption(evidence_text)


if not AuthManager.check_auth():
    st.warning("Inicia sesión para acceder a tus repasos.")
    st.stop()

load_css()
render_header(
    title="Centro de Repaso Inteligente",
    subtitle="Repasa en el momento adecuado y aprende de la causa de cada error",
)

user_id = st.session_state.get("user_id")
now = datetime.datetime.utcnow()

db = SessionLocal()
competition_id = get_active_competition_id(db, user_id)
try:
    eligible_question_ids = {
        question.question_id
        for question in QuestionService.get_questions_for_user(
            db, user_id, competition_id=competition_id
        )
    }
    due_count = db.query(QuestionPerformance).join(Question).filter(
        Question.competition_id == competition_id,
        Question.question_id.in_(eligible_question_ids),
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
    [f"🧠 Repasos de hoy ({due_count})", "📓 Cuaderno de errores", "⭐ Favoritas"]
)

with review_tab:
    st.markdown("### Cola de repaso espaciado")
    st.caption(
        "Tu respuesta, seguridad y tipo de error determinan cuándo volverás a ver cada pregunta."
    )

    review_day = datetime.date.today().isoformat()
    if st.session_state.get("native_review_day") != review_day:
        st.session_state["native_review_day"] = review_day
        st.session_state["native_review_completed"] = 0
        st.session_state.pop("native_review_target", None)
        st.session_state.pop("voluntary_review_ids", None)

    queue_db = SessionLocal()
    try:
        due_rows = queue_db.query(QuestionPerformance).join(Question).filter(
            Question.competition_id == competition_id,
            Question.question_id.in_(eligible_question_ids),
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
        upcoming_rows = queue_db.query(QuestionPerformance).join(Question).filter(
            Question.competition_id == competition_id,
            Question.question_id.in_(eligible_question_ids),
            QuestionPerformance.user_id == user_id,
            QuestionPerformance.next_review > now,
        ).order_by(QuestionPerformance.next_review.asc()).all()
        voluntary_ids = list(st.session_state.get("voluntary_review_ids", []))
        if not review_queue and voluntary_ids:
            review_queue = voluntary_ids[:20]
    finally:
        queue_db.close()

    if not review_queue:
        st.success("No tienes repasos vencidos hoy.")
        if upcoming_rows:
            next_review = upcoming_rows[0].next_review
            st.metric("Repasos programados", len(upcoming_rows))
            st.caption(
                f"Próximo repaso: {next_review.strftime('%d/%m/%Y')} · "
                "hasta entonces puedes continuar con el plan diario."
            )
        else:
            st.caption("Aún no hay repasos programados. Se crearán al responder y corregir preguntas.")

        optional_db = SessionLocal()
        try:
            optional_ids = [row.question_id for row in optional_db.query(QuestionPerformance).join(Question).filter(
                Question.competition_id == competition_id,
                Question.question_id.in_(eligible_question_ids),
                QuestionPerformance.user_id == user_id,
                QuestionPerformance.misses > 0,
            ).order_by(QuestionPerformance.misses.desc()).limit(5).all()]
        finally:
            optional_db.close()
        action_cols = st.columns(2)
        with action_cols[0]:
            if optional_ids and st.button("Repasar 5 errores ahora", use_container_width=True):
                st.session_state["voluntary_review_ids"] = optional_ids
                st.session_state["native_review_completed"] = 0
                st.session_state["native_review_target"] = len(optional_ids)
                st.rerun()
        with action_cols[1]:
            continue_label = (
                "Continuar al estudio guiado"
                if st.session_state.get("continue_daily_after_review")
                else "Continuar plan diario"
            )
            if st.button(continue_label, type="primary", use_container_width=True):
                if st.session_state.pop("continue_daily_after_review", None):
                    st.session_state["start_daily_after_review"] = True
                st.switch_page("pages/6_Dashboard.py")
    else:
        if st.session_state.get("continue_daily_after_review"):
            st.progress(0.05, text="Paso previo · Repasos vencidos")
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
            target = int(st.session_state.get("native_review_target") or (completed + len(review_queue)))
            target = max(1, min(20, target))
            st.session_state["native_review_target"] = target
            st.progress(min(completed / target, 1.0))
            st.caption(f"Repaso {completed + 1} de {target} · Tema: {question.topic}")
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
                explain_key = f"show_review_explanation_{current_question_id}"
                if is_correct:
                    st.success("Respuesta correcta.")
                else:
                    st.error(
                        f"La respuesta correcta es {question.correct_key}) "
                        f"{question.options_json.get(question.correct_key, '')}"
                    )
                if st.button(
                    "Ver explicación y recomendación",
                    key=f"explain_btn_{current_question_id}",
                    use_container_width=True,
                ):
                    st.session_state[explain_key] = True
                if st.session_state.get(explain_key, False):
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
                    schedule = record_attempt(
                        review_db, user_id=user_id, question=question,
                        chosen_key=chosen_key,
                        confidence=CONFIDENCE_OPTIONS[confidence_label],
                        error_type=ERROR_TYPES.get(error_label) if error_label else None,
                        when=review_time,
                    )
                    if is_correct:
                        question.global_hits = int(question.global_hits or 0) + 1
                    else:
                        question.global_misses = int(question.global_misses or 0) + 1
                    review_db.commit()
                    st.toast(
                        "Aprendizaje guardado y repaso actualizado.",
                        icon="✅",
                    )
                    st.session_state["native_review_completed"] = completed + 1
                    if st.session_state.get("voluntary_review_ids"):
                        st.session_state["voluntary_review_ids"] = [
                            item for item in st.session_state["voluntary_review_ids"]
                            if item != question.question_id
                        ]
                    st.session_state.pop("native_review_feedback", None)
                    st.session_state.pop(explain_key, None)
                    st.rerun()

            render_favorite_button(question.question_id, user_id)
        finally:
            review_db.close()

with errors_tab:
    st.markdown("### Cuaderno de errores")
    st.caption(
        "Cada episodio conserva su diagnóstico, regla, fuente y evidencia de transferencia."
    )
    errors_db = SessionLocal()
    try:
        if _canonical_error_notebook_available(errors_db):
            _render_canonical_error_notebook(
                errors_db,
                user_id=user_id,
                competition_id=competition_id,
                now=now,
            )
        else:
            _render_legacy_error_bank(
                errors_db,
                user_id=user_id,
                competition_id=competition_id,
                eligible_question_ids=eligible_question_ids,
            )
    finally:
        errors_db.close()

with favorites_tab:
    st.markdown("### Preguntas favoritas")
    favorites_db = SessionLocal()
    try:
        favorite_rows = favorites_db.query(QuestionPerformance).join(Question).filter(
            Question.competition_id == competition_id,
            Question.question_id.in_(eligible_question_ids),
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

