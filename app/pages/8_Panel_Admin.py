import streamlit as st
import os, sys, pandas as pd
import datetime
import time
from pathlib import Path
from sqlalchemy import Integer, func

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import (
    User, UserStats, UserOPEC, Attempt, Question, QuestionAnkiEnrichment,
    NormativaChunk, Competition, OpecProfile, OpecSimulationPolicy,
)
from ui_utils import load_css, log_ui_exception, render_header
from core.access_control import require_admin
from core.normativa import NormativaManager
from core.anki_enrichment import backfill_enrichments
from core.admin_opec_assignment import AssignableOPECNotFound, assign_prepared_opec
from core.config import get_api_key
from core.ai.usage_policy import AIUsageLimitError, reserve_ai_usage
from core.safe_uploads import (
    DEFAULT_DOCUMENT_LIMITS,
    UnsafeUpload,
    atomic_write,
    confined_destination,
    sanitize_upload_name,
    validate_pdf,
)
from core.simulation_policy import SimulationPolicyValidationError
from core.simulation_policy_store import (
    SimulationPolicyStoreError,
    create_initial_simulation_policy,
    create_simulation_policy_version,
    load_active_simulation_policy,
    simulation_policy_schema_available,
)


OPEC_236769_OFFICIAL_PARTIAL = {
    "official_max_questions_per_case": 3,
    "official_source_title": "CNSC · Especificaciones técnicas LP-004-2026",
    "official_source_url": (
        "https://community.secop.gov.co/Public/Archive/RetrieveFile/Index"
        "?DocumentId=783745811&InCommunity=False&InPaymentGateway=False"
    ),
    "official_source_version": "LP-004-2026",
    "official_source_status": "partial",
}

NAVIGATION_LABELS = {
    "sequential": "Secuencial",
    "case_locked": "Bloqueada por caso",
    "free": "Libre",
}
OFFICIAL_STATUS_LABELS = {
    None: "Sin estado publicado",
    "unpublished": "No publicado",
    "pending_verification": "Pendiente de contraste",
    "partial": "Evidencia parcial",
    "verified_current": "Verificada vigente",
    "superseded": "Reemplazada",
}


def _optional_admin_int(raw_value, label):
    text_value = str(raw_value or "").strip()
    if not text_value:
        return None
    try:
        return int(text_value)
    except ValueError as exc:
        raise SimulationPolicyValidationError(
            f"{label} debe ser un número entero o quedar vacío."
        ) from exc


def _optional_admin_float(raw_value, label):
    text_value = str(raw_value or "").strip().replace(",", ".")
    if not text_value:
        return None
    try:
        return float(text_value)
    except ValueError as exc:
        raise SimulationPolicyValidationError(
            f"{label} debe ser un número o quedar vacío."
        ) from exc

# pass # Removed st.set_page_config

require_admin()

load_css()
render_header(title="Panel de Control", subtitle="Estado de la app y gestión de usuarios")

tab_stats, tab_users, tab_simulation_policy, tab_technical = st.tabs([
    "📊 Estado general", "👥 Usuarios", "🎛️ Política de simulacros", "⚙️ Opciones técnicas"
])
with tab_technical:
    st.info(
        "Estas herramientas son de mantenimiento. No habilitan preguntas ni sustituyen el "
        "Centro de Calidad, que es donde se controla el banco y sus fuentes."
    )
    tab_normativa, tab_anki = st.tabs(["📚 Biblioteca normativa", "🎴 Repasos Anki"])

# --- TAB: STATS ---
with tab_stats:
    db = SessionLocal()
    try:
        now = datetime.datetime.now()
        cutoff_7d = now - datetime.timedelta(days=7)
        cutoff_30d = now - datetime.timedelta(days=30)
        total_users = db.query(User).count()
        active_users_7d = (
            db.query(Attempt.user_id)
            .filter(Attempt.created_at >= cutoff_7d, Attempt.user_id.isnot(None))
            .distinct()
            .count()
        )
        total_attempts = db.query(Attempt).count()
        attempts_30d = db.query(Attempt).filter(Attempt.created_at >= cutoff_30d).count()
        correct_30d = db.query(Attempt).filter(
            Attempt.created_at >= cutoff_30d, Attempt.is_correct.is_(True)
        ).count()
        total_points = db.query(func.sum(UserStats.total_points)).scalar() or 0
        total_questions = db.query(Question).count()
        verified_questions = db.query(Question).filter(Question.is_verified.is_(True)).count()
        situational_questions = db.query(Question).filter_by(question_type="SITUATIONAL").count()
        sourced_questions = db.query(Question).filter(
            Question.source_refs.isnot(None), Question.source_refs != ""
        ).count()
        recent_attempts = db.query(Attempt).filter(
            Attempt.created_at >= cutoff_30d
        ).order_by(Attempt.created_at.asc()).all()
    finally:
        db.close()

    accuracy_30d = round(correct_30d * 100 / attempts_30d) if attempts_30d else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Usuarios registrados", total_users)
    col2.metric("Activos en 7 días", active_users_7d, help="Usuarios distintos que respondieron al menos una pregunta.")
    col3.metric("Respuestas en 30 días", attempts_30d, help=f"{total_attempts} respuestas acumuladas.")
    col4.metric("Precisión en 30 días", f"{accuracy_30d}%" if attempts_30d else "Sin datos")

    st.subheader("📈 Actividad de los últimos 30 días")
    if recent_attempts:
        activity_rows = [
            {"Fecha": item.created_at.date(), "Correcta": int(bool(item.is_correct))}
            for item in recent_attempts
        ]
        activity_df = pd.DataFrame(activity_rows)
        daily_activity = activity_df.groupby("Fecha").agg(
            Respuestas=("Correcta", "size"), Aciertos=("Correcta", "sum")
        )
        daily_activity["Precisión (%)"] = (
            daily_activity["Aciertos"] * 100 / daily_activity["Respuestas"]
        ).round(1)
        st.bar_chart(daily_activity[["Respuestas"]], height=220)
        st.dataframe(
            daily_activity.reset_index().sort_values("Fecha", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Todavía no hay respuestas registradas en los últimos 30 días.")

    st.subheader("📚 Resumen del banco")
    bank1, bank2, bank3 = st.columns(3)
    bank1.metric("Preguntas", total_questions)
    bank2.metric(
        "Verificadas",
        f"{round(verified_questions * 100 / total_questions) if total_questions else 0}%",
        help=f"{verified_questions} preguntas marcadas como verificadas.",
    )
    bank3.metric(
        "Situacionales",
        f"{round(situational_questions * 100 / total_questions) if total_questions else 0}%",
        help=f"{situational_questions} preguntas tienen formato situacional.",
    )
    missing_sources = max(total_questions - sourced_questions, 0)
    if missing_sources:
        st.warning(f"Hay {missing_sources} preguntas sin referencia documental registrada.")
    else:
        st.success("Todas las preguntas tienen una referencia documental registrada.")
    st.caption(
        f"Puntos acumulados por todos los usuarios: {total_points:,}. "
        "Las cifras de esta pestaña abarcan todos los concursos registrados."
    )
    st.info("Para revisar fuentes, estructura y estados del banco, usa **Banco de preguntas → Centro de calidad**.")

# --- TAB: USERS ---
with tab_users:
    st.subheader("👥 Seguimiento de usuarios")
    st.caption("Consulta actividad y avance. Puedes asignar una OPEC preparada, sin modificar contraseñas ni permisos.")
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.username).all()
        stats_by_user = {item.user_id: item for item in db.query(UserStats).all()}
        opec_rows = db.query(UserOPEC).order_by(UserOPEC.updated_at.desc()).all()
        opecs_by_user = {}
        for item in opec_rows:
            opecs_by_user.setdefault(item.user_id, []).append(item)
        attempt_summary = {
            row.user_id: {"answers": row.answers, "hits": row.hits or 0, "last": row.last_attempt}
            for row in (
                db.query(
                    Attempt.user_id,
                    func.count(Attempt.attempt_id).label("answers"),
                    func.sum(func.cast(Attempt.is_correct, Integer)).label("hits"),
                    func.max(Attempt.created_at).label("last_attempt"),
                )
                .filter(Attempt.user_id.isnot(None))
                .group_by(Attempt.user_id)
                .all()
            )
        }
        user_data = []
        now_users = datetime.datetime.now()
        for user in users:
            stats = stats_by_user.get(user.id)
            activity = attempt_summary.get(user.id, {"answers": 0, "hits": 0, "last": None})
            last_attempt = activity["last"]
            if last_attempt and last_attempt >= now_users - datetime.timedelta(days=7):
                activity_label = "Activo"
            elif last_attempt and last_attempt >= now_users - datetime.timedelta(days=30):
                activity_label = "Inactivo 7+ días"
            elif last_attempt:
                activity_label = "Inactivo 30+ días"
            else:
                activity_label = "Sin iniciar"
            accuracy = round(activity["hits"] * 100 / activity["answers"]) if activity["answers"] else None
            user_data.append({
                "ID": user.id,
                "Usuario": user.username,
                "Rol": user.role,
                "Plan": user.subscription_tier or "free",
                "Estado": activity_label,
                "Respuestas": activity["answers"],
                "Precisión": f"{accuracy}%" if accuracy is not None else "—",
                "Racha": stats.current_streak if stats else 0,
                "Puntos": stats.total_points if stats else 0,
                "OPEC": len(opecs_by_user.get(user.id, [])),
                "Última práctica": last_attempt.strftime("%Y-%m-%d") if last_attempt else "—",
                "Registro": user.created_at.strftime("%Y-%m-%d") if user.created_at else "—",
            })
    finally:
        db.close()

    df_users = pd.DataFrame(user_data)
    filter_col1, filter_col2 = st.columns([2, 1])
    search_user = filter_col1.text_input("Buscar usuario", placeholder="Escribe el nombre...")
    role_options = ["Todos"] + sorted(df_users["Rol"].dropna().unique().tolist()) if not df_users.empty else ["Todos"]
    role_filter = filter_col2.selectbox("Rol", role_options)
    filtered_users = df_users.copy()
    if search_user:
        filtered_users = filtered_users[
            filtered_users["Usuario"].str.contains(search_user, case=False, na=False)
        ]
    if role_filter != "Todos":
        filtered_users = filtered_users[filtered_users["Rol"] == role_filter]

    st.dataframe(filtered_users, use_container_width=True, hide_index=True)
    st.caption(f"Mostrando {len(filtered_users)} de {len(df_users)} usuarios.")

    if user_data:
        with st.expander("Ver detalle de un usuario"):
            selected_username = st.selectbox(
                "Usuario",
                [item["Usuario"] for item in user_data],
                key="admin_user_detail",
            )
            selected = next(item for item in user_data if item["Usuario"] == selected_username)
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Estado", selected["Estado"])
            d2.metric("Respuestas", selected["Respuestas"])
            d3.metric("Precisión", selected["Precisión"])
            d4.metric("Racha", f"{selected['Racha']} días")
            selected_opecs = opecs_by_user.get(selected["ID"], [])
            if selected_opecs:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "OPEC": item.opec_number,
                            "Cargo": item.job_title,
                            "Nivel": item.level or "—",
                            "Activa": "Sí" if item.is_active else "No",
                        }
                        for item in selected_opecs
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Este usuario todavía no ha configurado una OPEC.")

        with st.expander("Asignar una OPEC preparada a un usuario"):
            st.caption(
                "La asignación activa esa OPEC para la cuenta seleccionada. "
                "Solo usa fichas que ya existan en el catálogo o banco compartido."
            )
            user_options = {
                f"{item['Usuario']} · ID {item['ID']}": item["ID"]
                for item in user_data
            }
            with st.form("admin_assign_prepared_opec"):
                target_label = st.selectbox("Usuario", list(user_options))
                target_opec = st.text_input("Número OPEC", placeholder="Ej.: 242699")
                assign_requested = st.form_submit_button("Asignar y activar OPEC", type="primary")
            if assign_requested:
                if not target_opec.strip():
                    st.error("Indica el número OPEC que quieres asignar.")
                else:
                    assign_db = SessionLocal()
                    try:
                        assigned = assign_prepared_opec(
                            assign_db,
                            user_options[target_label],
                            target_opec,
                            actor_user_id=st.session_state.get("user_id"),
                        )
                        assign_db.commit()
                        st.success(
                            f"OPEC {assigned.opec_number} asignada y activada para {target_label.split(' · ')[0]}."
                        )
                    except AssignableOPECNotFound as exc:
                        assign_db.rollback()
                        st.warning(str(exc))
                    except Exception as exc:
                        assign_db.rollback()
                        log_ui_exception("admin.opec_assignment", exc)
                        st.error("No se pudo asignar la OPEC en este momento.")
                    finally:
                        assign_db.close()

    st.caption("🔒 Los roles, contraseñas y permisos no se modifican desde esta pantalla.")

# --- TAB: OPEC SIMULATION POLICY ---
with tab_simulation_policy:
    st.subheader("🎛️ Política de simulacros por OPEC")
    st.caption(
        "Configura los tamaños y tiempos internos sin presentarlos como condiciones oficiales. "
        "Cada cambio crea una versión nueva y conserva el historial anterior."
    )
    policy_flash = st.session_state.pop("admin_simulation_policy_flash", None)
    if policy_flash:
        st.success(policy_flash)

    db_policy = SessionLocal()
    try:
        if not simulation_policy_schema_available(db_policy):
            st.warning(
                "La tabla de políticas aún no está disponible. Aplica primero la migración aditiva de Fase 3."
            )
        else:
            profile_rows = (
                db_policy.query(OpecProfile, Competition.name)
                .outerjoin(Competition, Competition.id == OpecProfile.competition_id)
                .order_by(OpecProfile.opec_number.asc(), OpecProfile.id.asc())
                .all()
            )
            profile_options = [
                {
                    "id": profile.id,
                    "competition_id": profile.competition_id,
                    "competition_name": competition_name or f"Concurso {profile.competition_id}",
                    "opec_number": profile.opec_number,
                    "job_title": profile.job_title or "Cargo sin denominación",
                }
                for profile, competition_name in profile_rows
            ]

            if not profile_options:
                st.info(
                    "Todavía no hay perfiles OPEC canónicos. Registra y prepara una OPEC antes de definir su política."
                )
            else:
                selected_profile_index = st.selectbox(
                    "Perfil OPEC",
                    range(len(profile_options)),
                    format_func=lambda index: (
                        f"OPEC {profile_options[index]['opec_number']} · "
                        f"{profile_options[index]['job_title']} · "
                        f"{profile_options[index]['competition_name']}"
                    ),
                    key="admin_simulation_policy_profile",
                )
                selected_profile = profile_options[selected_profile_index]
                profile, active_policy, resolved_policy = load_active_simulation_policy(
                    db_policy,
                    competition_id=selected_profile["competition_id"],
                    opec_number=selected_profile["opec_number"],
                )
                policy_history = (
                    db_policy.query(OpecSimulationPolicy)
                    .filter_by(opec_profile_id=profile.id)
                    .order_by(OpecSimulationPolicy.version_number.desc())
                    .all()
                )

                if not policy_history:
                    st.warning(
                        "Esta OPEC todavía no tiene historial. La versión inicial será provisional y sus "
                        "cantidades y tiempos serán parámetros internos."
                    )
                    if profile.opec_number == "236769":
                        st.info(
                            "Para OPEC 236769 se registrará únicamente la evidencia parcial de LP-004-2026: "
                            "hasta 3 preguntas por caso. La cantidad total y la duración oficiales permanecerán vacías."
                        )
                    if st.button(
                        "Crear versión inicial v1",
                        type="primary",
                        use_container_width=True,
                        key=f"create_initial_policy_{profile.id}",
                    ):
                        try:
                            official_partial = (
                                dict(OPEC_236769_OFFICIAL_PARTIAL)
                                if profile.opec_number == "236769"
                                else None
                            )
                            created_policy = create_initial_simulation_policy(
                                db_policy,
                                competition_id=profile.competition_id,
                                opec_number=profile.opec_number,
                                actor=(
                                    st.session_state.get("username")
                                    or f"admin:{st.session_state.get('user_id')}"
                                ),
                                official_partial=official_partial,
                            )
                            db_policy.commit()
                            st.session_state["admin_simulation_policy_flash"] = (
                                f"Se creó {created_policy.policy_version} como política provisional."
                            )
                            st.rerun()
                        except (
                            SimulationPolicyStoreError,
                            SimulationPolicyValidationError,
                        ) as exc:
                            db_policy.rollback()
                            st.warning(str(exc))
                        except Exception as exc:
                            db_policy.rollback()
                            log_ui_exception("admin.simulation_policy.create", exc)
                            st.error("No fue posible crear la política inicial.")
                elif active_policy is None:
                    st.error(
                        "La OPEC tiene historial, pero ninguna versión activa. Revisa la migración o el historial antes de continuar."
                    )
                else:
                    version_col, status_col, nav_col, case_col = st.columns(4)
                    version_col.metric("Versión activa", active_policy.policy_version)
                    status_col.metric("Estado", active_policy.policy_status.capitalize())
                    nav_col.metric(
                        "Navegación interna",
                        NAVIGATION_LABELS.get(
                            resolved_policy.internal.navigation_mode,
                            resolved_policy.internal.navigation_mode,
                        ),
                    )
                    case_col.metric(
                        "Máximo por caso",
                        resolved_policy.internal.max_questions_per_case,
                    )

                    st.markdown("**Parámetros internos de práctica**")
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Modo": mode.label,
                                    "Preguntas": mode.question_count,
                                    "Duración estimada": f"{mode.duration_minutes} min",
                                }
                                for mode in resolved_policy.internal.modes
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(
                        f"Ritmo interno: {resolved_policy.internal.minutes_per_question:g} min/pregunta. "
                        "Estos valores son decisiones del simulador, no datos publicados por la CNSC."
                    )

                    st.markdown("**Evidencia y parámetros oficiales, si están publicados**")
                    official = resolved_policy.official
                    official_cols = st.columns(4)
                    official_cols[0].metric(
                        "Cantidad oficial",
                        official.question_count if official.question_count is not None else "No publicada",
                    )
                    official_cols[1].metric(
                        "Duración oficial",
                        f"{official.duration_minutes} min"
                        if official.duration_minutes is not None
                        else "No publicada",
                    )
                    official_cols[2].metric(
                        "Ritmo oficial",
                        f"{official.minutes_per_question:g} min/pregunta"
                        if official.minutes_per_question is not None
                        else "No publicado",
                    )
                    official_cols[3].metric(
                        "Máximo oficial por caso",
                        official.max_questions_per_case
                        if official.max_questions_per_case is not None
                        else "No publicado",
                    )
                    if official.source_url:
                        st.link_button(
                            official.source_title or "Abrir fuente oficial registrada",
                            official.source_url,
                        )
                        st.caption(
                            f"Fuente: {official.source_version or 'sin versión'} · "
                            f"Estado: {OFFICIAL_STATUS_LABELS.get(official.source_status, official.source_status)}"
                        )
                    else:
                        st.info("Esta política todavía no tiene una fuente oficial enlazada.")
                    st.caption(
                        "Los campos oficiales son opcionales e independientes. Dejar un campo vacío guarda NULL; "
                        "nunca se completa con el valor interno."
                    )

                    with st.expander("Crear una versión nueva", expanded=False):
                        with st.form(
                            f"new_simulation_policy_{profile.id}_{active_policy.version_number}"
                        ):
                            st.markdown("**Configuración interna**")
                            mode_counts = {
                                mode.key: mode.question_count
                                for mode in resolved_policy.internal.modes
                            }
                            count_cols = st.columns(4)
                            diagnostic_count = count_cols[0].number_input(
                                "Diagnóstico",
                                min_value=1,
                                max_value=5000,
                                value=int(mode_counts["diagnostic"]),
                                step=1,
                            )
                            short_count = count_cols[1].number_input(
                                "Corto",
                                min_value=1,
                                max_value=5000,
                                value=int(mode_counts["short"]),
                                step=1,
                            )
                            partial_count = count_cols[2].number_input(
                                "Parcial",
                                min_value=1,
                                max_value=5000,
                                value=int(mode_counts["partial"]),
                                step=1,
                            )
                            full_count = count_cols[3].number_input(
                                "Completo",
                                min_value=1,
                                max_value=5000,
                                value=int(mode_counts["full"]),
                                step=1,
                            )
                            internal_cols = st.columns(3)
                            minutes_per_question = internal_cols[0].number_input(
                                "Minutos por pregunta",
                                min_value=0.1,
                                max_value=60.0,
                                value=float(resolved_policy.internal.minutes_per_question),
                                step=0.1,
                                format="%.1f",
                            )
                            max_questions_per_case = internal_cols[1].number_input(
                                "Máximo de preguntas por caso",
                                min_value=1,
                                max_value=10,
                                value=int(resolved_policy.internal.max_questions_per_case),
                                step=1,
                            )
                            navigation_options = list(NAVIGATION_LABELS)
                            navigation_mode = internal_cols[2].selectbox(
                                "Navegación",
                                navigation_options,
                                index=navigation_options.index(
                                    resolved_policy.internal.navigation_mode
                                ),
                                format_func=lambda value: NAVIGATION_LABELS[value],
                            )

                            st.divider()
                            st.markdown("**Campos oficiales opcionales**")
                            st.caption(
                                "Escribe únicamente valores respaldados por la fuente enlazada. Vacío significa no publicado."
                            )
                            official_input_cols = st.columns(2)
                            official_question_count_raw = official_input_cols[0].text_input(
                                "Cantidad total oficial",
                                value=(
                                    str(official.question_count)
                                    if official.question_count is not None
                                    else ""
                                ),
                                placeholder="Vacío = NULL",
                            )
                            official_duration_raw = official_input_cols[1].text_input(
                                "Duración oficial en minutos",
                                value=(
                                    str(official.duration_minutes)
                                    if official.duration_minutes is not None
                                    else ""
                                ),
                                placeholder="Vacío = NULL",
                            )
                            official_minutes_raw = official_input_cols[0].text_input(
                                "Minutos oficiales por pregunta",
                                value=(
                                    str(official.minutes_per_question)
                                    if official.minutes_per_question is not None
                                    else ""
                                ),
                                placeholder="Vacío = NULL",
                            )
                            official_max_case_raw = official_input_cols[1].text_input(
                                "Máximo oficial de preguntas por caso",
                                value=(
                                    str(official.max_questions_per_case)
                                    if official.max_questions_per_case is not None
                                    else ""
                                ),
                                placeholder="Vacío = NULL",
                            )
                            official_navigation_options = [None, *navigation_options]
                            official_navigation = st.selectbox(
                                "Navegación oficial",
                                official_navigation_options,
                                index=official_navigation_options.index(
                                    official.navigation_mode
                                ),
                                format_func=lambda value: (
                                    "No publicada"
                                    if value is None
                                    else NAVIGATION_LABELS[value]
                                ),
                            )
                            source_cols = st.columns(2)
                            source_title = source_cols[0].text_input(
                                "Título de la fuente oficial",
                                value=official.source_title or "",
                            )
                            source_version = source_cols[1].text_input(
                                "Versión o fecha de la fuente",
                                value=official.source_version or "",
                            )
                            source_url = st.text_input(
                                "URL oficial HTTPS",
                                value=official.source_url or "",
                            )
                            source_status_options = list(OFFICIAL_STATUS_LABELS)
                            source_status = st.selectbox(
                                "Estado de la fuente",
                                source_status_options,
                                index=source_status_options.index(official.source_status),
                                format_func=lambda value: OFFICIAL_STATUS_LABELS[value],
                            )

                            change_reason = st.text_area(
                                "Motivo de la nueva versión",
                                placeholder="Describe qué cambió y por qué.",
                                help="Obligatorio para conservar una auditoría comprensible.",
                            )
                            create_version = st.form_submit_button(
                                "Crear y activar nueva versión",
                                type="primary",
                                use_container_width=True,
                            )

                        if create_version:
                            try:
                                if not change_reason.strip():
                                    raise SimulationPolicyStoreError(
                                        "Explica el motivo del cambio de política."
                                    )
                                if source_url.strip() and not source_url.strip().lower().startswith(
                                    "https://"
                                ):
                                    raise SimulationPolicyValidationError(
                                        "La fuente oficial debe usar una URL HTTPS."
                                    )
                                updates = {
                                    "internal_diagnostic_questions": int(diagnostic_count),
                                    "internal_short_questions": int(short_count),
                                    "internal_partial_questions": int(partial_count),
                                    "internal_full_questions": int(full_count),
                                    "internal_minutes_per_question": float(minutes_per_question),
                                    "internal_max_questions_per_case": int(max_questions_per_case),
                                    "internal_navigation_mode": navigation_mode,
                                    "policy_status": "provisional",
                                    "official_question_count": _optional_admin_int(
                                        official_question_count_raw,
                                        "Cantidad oficial",
                                    ),
                                    "official_duration_minutes": _optional_admin_int(
                                        official_duration_raw,
                                        "Duración oficial",
                                    ),
                                    "official_minutes_per_question": _optional_admin_float(
                                        official_minutes_raw,
                                        "Minutos oficiales por pregunta",
                                    ),
                                    "official_max_questions_per_case": _optional_admin_int(
                                        official_max_case_raw,
                                        "Máximo oficial por caso",
                                    ),
                                    "official_navigation_mode": official_navigation,
                                    "official_source_title": source_title.strip() or None,
                                    "official_source_url": source_url.strip() or None,
                                    "official_source_version": source_version.strip() or None,
                                    "official_source_status": source_status,
                                }
                                new_policy = create_simulation_policy_version(
                                    db_policy,
                                    current=active_policy,
                                    updates=updates,
                                    actor=(
                                        st.session_state.get("username")
                                        or f"admin:{st.session_state.get('user_id')}"
                                    ),
                                    change_reason=change_reason,
                                )
                                db_policy.commit()
                                st.session_state["admin_simulation_policy_flash"] = (
                                    f"Se creó y activó {new_policy.policy_version}; la versión anterior quedó en el historial."
                                )
                                st.rerun()
                            except (
                                SimulationPolicyStoreError,
                                SimulationPolicyValidationError,
                            ) as exc:
                                db_policy.rollback()
                                st.warning(str(exc))
                            except Exception as exc:
                                db_policy.rollback()
                                log_ui_exception("admin.simulation_policy.version", exc)
                                st.error("No fue posible crear la nueva versión.")

                    with st.expander(f"Historial ({len(policy_history)} versiones)"):
                        st.dataframe(
                            pd.DataFrame(
                                [
                                    {
                                        "Versión": item.policy_version,
                                        "Estado": item.policy_status,
                                        "Activa": "Sí" if item.is_active else "No",
                                        "Motivo": item.change_reason or "—",
                                        "Actor": item.actor or "—",
                                        "Creada": (
                                            item.created_at.strftime("%Y-%m-%d %H:%M")
                                            if item.created_at
                                            else "—"
                                        ),
                                    }
                                    for item in policy_history
                                ]
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )
    except (SimulationPolicyStoreError, SimulationPolicyValidationError) as exc:
        db_policy.rollback()
        st.warning(str(exc))
    except Exception as exc:
        db_policy.rollback()
        log_ui_exception("admin.simulation_policy.load", exc)
        st.error("No fue posible cargar las políticas de simulacro.")
    finally:
        db_policy.close()

# --- TAB: NORMATIVA ---
with tab_normativa:
    st.subheader("📚 Biblioteca normativa técnica")
    st.caption(
        "Archivo técnico para documentos PDF y búsqueda semántica. No modifica ni certifica "
        "preguntas automáticamente; el control de fuentes vive en el Centro de Calidad."
    )
    norm_path = Path(PROJECT_ROOT) / "data" / "normativa"
    norm_path.mkdir(parents=True, exist_ok=True)

    files = sorted(p.name for p in norm_path.glob("*.pdf"))
    db_norm = SessionLocal()
    try:
        chunk_count = db_norm.query(NormativaChunk).count()
        vector_count = db_norm.query(NormativaChunk).filter(
            NormativaChunk.embedding_json.isnot(None)
        ).count()
        indexed_sources = db_norm.query(NormativaChunk.source_file).distinct().count()
        source_rows = (
            db_norm.query(
                NormativaChunk.source_file,
                func.count(NormativaChunk.id).label("fragmentos"),
                func.count(NormativaChunk.embedding_json).label("vectores"),
            )
            .group_by(NormativaChunk.source_file)
            .order_by(NormativaChunk.source_file)
            .all()
        )
    finally:
        db_norm.close()

    c1, c2, c3 = st.columns(3)
    c1.metric("PDF disponibles", len(files))
    c2.metric("Documentos procesados", indexed_sources)
    c3.metric(
        "Búsqueda semántica",
        f"{round(vector_count * 100 / chunk_count) if chunk_count else 0}%",
        help=f"{vector_count} de {chunk_count} fragmentos tienen vector semántico.",
    )

    if source_rows:
        st.dataframe(
            pd.DataFrame(source_rows, columns=["Documento", "Fragmentos", "Vectores"]),
            use_container_width=True,
            hide_index=True,
        )
    elif files:
        st.info("Hay PDF disponibles, pero todavía no se han procesado.")
    else:
        st.info("La biblioteca está vacía. Sube el primer PDF para comenzar.")

    st.subheader("1. Agregar o actualizar un documento")
    uploaded_file = st.file_uploader(
        "Selecciona una ley, decreto, estatuto o guía en PDF",
        type="pdf",
        help=(
            "El texto extraído quedará guardado en la base de datos. "
            f"Límite de la app: {DEFAULT_DOCUMENT_LIMITS.max_pdf_bytes // (1024 * 1024)} MB "
            f"y {DEFAULT_DOCUMENT_LIMITS.max_pdf_pages} páginas."
        ),
    )
    if uploaded_file is not None:
        upload_ready = False
        safe_name = ""
        payload = b""
        try:
            safe_name = sanitize_upload_name(
                uploaded_file.name, allowed_suffixes=(".pdf",)
            )
            payload = bytes(uploaded_file.getbuffer())
            validate_pdf(payload)
            destination = confined_destination(norm_path, safe_name)
            upload_ready = True
        except UnsafeUpload as exc:
            st.error(str(exc))

        already_exists = upload_ready and destination.exists()
        if already_exists:
            st.warning(
                f"{safe_name} ya existe. Para evitar mezclar una versión anterior con otra nueva, "
                "cambia el nombre del archivo antes de cargarlo."
            )
        if st.button(
            "📥 Guardar y procesar PDF",
            type="primary",
            use_container_width=True,
            disabled=not upload_ready or already_exists,
        ):
            manager = NormativaManager(str(norm_path))
            try:
                atomic_write(destination, payload)
                with st.spinner("Leyendo y preparando el documento..."):
                    indexed = manager.index_all()
                if indexed:
                    st.success(f"{safe_name} quedó listo: se agregaron {indexed} fragmentos nuevos.")
                else:
                    st.info(f"{safe_name} ya estaba procesado; no se encontraron fragmentos nuevos.")
                st.rerun()
            except UnsafeUpload as exc:
                st.error(str(exc))
            except Exception as exc:
                log_ui_exception("admin.library.pdf_upload", exc)
                st.error("No fue posible procesar el PDF. Revisa el archivo e inténtalo de nuevo.")

    st.subheader("2. Mantenimiento de la biblioteca")
    st.caption("Usa estas acciones solo al agregar archivos directamente al repositorio o si faltan vectores.")
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        if st.button("🔄 Procesar PDF pendientes", use_container_width=True, help="Extrae el texto de los PDF disponibles y evita fragmentos duplicados"):
            manager = NormativaManager(str(norm_path))
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_cb(pct, msg):
                progress_bar.progress(pct / 100.0)
                status_text.text(msg)
                
            try:
                indexed = manager.index_all(progress_callback=progress_cb)
                if indexed:
                    st.success(f"Se agregaron {indexed} fragmentos nuevos.")
                else:
                    st.info("Todo está al día; no había fragmentos nuevos.")
                st.rerun()
            except Exception as exc:
                log_ui_exception("admin.library.index", exc)
                st.error("No fue posible indexar los PDF pendientes.")
                
    with col_act2:
        missing_vectors = max(chunk_count - vector_count, 0)
        embedding_batch = st.number_input(
            "Vectores para completar ahora",
            min_value=1,
            max_value=50,
            value=min(25, max(missing_vectors, 1)),
            step=5,
            disabled=missing_vectors == 0,
            help="El límite por ejecución evita consumos accidentales de API.",
        )
        if st.button(
            f"🧠 Completar siguiente lote ({min(int(embedding_batch), missing_vectors)})",
            use_container_width=True,
            disabled=missing_vectors == 0,
            help="Genera con Gemini los vectores que permiten encontrar fuentes por significado.",
        ):
            if not get_api_key("gemini"):
                st.error("Configura una API key global de Gemini antes de generar los vectores.")
                st.stop()
            manager = NormativaManager(str(norm_path))
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_cb(pct, msg):
                progress_bar.progress(pct / 100.0)
                status_text.text(msg)
                
            try:
                updated = manager.backfill_embeddings(
                    progress_callback=progress_cb,
                    limit=int(embedding_batch),
                    user_id=st.session_state.get("user_id"),
                )
                st.success(f"Búsqueda semántica actualizada en {updated} fragmentos.")
                st.rerun()
            except AIUsageLimitError as exc:
                st.warning(str(exc))
            except Exception as exc:
                log_ui_exception("admin.library.embeddings", exc)
                st.error("No fue posible generar los vectores en este momento.")

    st.caption(
        "En Streamlit Cloud los PDF subidos al disco pueden desaparecer al reiniciar. "
        "Los fragmentos ya procesados permanecen si la base de datos configurada es persistente; "
        "para conservar también el archivo original, agrégalo al repositorio o usa almacenamiento externo."
    )

# --- TAB: ANKI ENRICHMENT ---
with tab_anki:
    st.subheader("🧠 Material de repaso explicado (técnico)")
    st.caption(
        "La IA prepara para cada pregunta una regla clave, una excepción y el distractor más engañoso. "
        "Este contenido mejora el repaso dentro de la app y también puede acompañar una exportación a Anki."
    )
    flash_anki = st.session_state.pop("admin_anki_result", None)
    if flash_anki:
        if flash_anki["errors"]:
            st.warning(
                f"Se prepararon {flash_anki['generated']} de {flash_anki['total']} preguntas; "
                f"{flash_anki['errors']} requieren otro intento."
            )
        else:
            st.success(f"Se prepararon {flash_anki['generated']} preguntas correctamente.")

    db_anki = SessionLocal()
    try:
        ready_count = db_anki.query(QuestionAnkiEnrichment).filter(
            QuestionAnkiEnrichment.status.in_(["generated", "reviewed"])
        ).count()
        reviewed_count = db_anki.query(QuestionAnkiEnrichment).filter_by(status="reviewed").count()
        error_count = db_anki.query(QuestionAnkiEnrichment).filter_by(status="error").count()
        total_questions_anki = db_anki.query(Question).count()
        recent_errors = (
            db_anki.query(QuestionAnkiEnrichment)
            .filter_by(status="error")
            .order_by(QuestionAnkiEnrichment.id.desc())
            .limit(10)
            .all()
        )
        error_rows = [
            {
                "Pregunta": item.question_id,
                "Intentos": item.attempt_count,
                "Motivo": item.error_message or "Error no especificado",
            }
            for item in recent_errors
        ]
    finally:
        db_anki.close()

    waiting_count = max(total_questions_anki - ready_count - error_count, 0)
    coverage = round(ready_count * 100 / total_questions_anki) if total_questions_anki else 0
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    col_a1.metric("Cobertura", f"{coverage}%", help=f"{ready_count} de {total_questions_anki} preguntas listas.")
    col_a2.metric("Listas para repaso", ready_count, help=f"{reviewed_count} fueron revisadas manualmente.")
    col_a3.metric("Sin preparar", waiting_count)
    col_a4.metric("Reintentar", error_count)

    st.progress(coverage / 100 if coverage else 0, text=f"Cobertura pedagógica: {coverage}%")
    if error_rows:
        with st.expander(f"Ver los últimos errores ({error_count})"):
            st.dataframe(pd.DataFrame(error_rows), use_container_width=True, hide_index=True)
            st.caption("Estos registros se vuelven a intentar automáticamente en la siguiente ejecución.")

    provider_anki = st.selectbox(
        "Proveedor de IA", ["Gemini", "OpenAI", "Groq", "Mistral"], key="admin_anki_provider",
        help="Se utiliza la clave global configurada por el administrador.",
    )
    provider_key = provider_anki.lower()
    api_key_anki = get_api_key(provider_key)
    if api_key_anki:
        st.caption(f"✅ {provider_anki} está configurado. Solo se enviará el lote seleccionado.")
    else:
        st.warning(f"Falta configurar la API key global de {provider_anki}.")

    batch_limit = st.number_input(
        "Preguntas para preparar ahora", min_value=1, max_value=25, value=10, step=5,
        help="Conviene trabajar en lotes pequeños para controlar costo y detectar fallos pronto.",
    )
    with st.expander("Opciones avanzadas"):
        force_regeneration = st.checkbox(
            "Volver a generar contenido existente que aún no ha sido revisado",
            value=False,
            help="Puede consumir más API. El contenido marcado como revisado se conserva.",
        )

    available_work = total_questions_anki - reviewed_count if force_regeneration else waiting_count + error_count
    run_count = min(int(batch_limit), max(available_work, 0))
    if st.button(
        f"🧠 Preparar siguiente lote ({run_count})",
        type="primary",
        use_container_width=True,
        disabled=not api_key_anki or run_count == 0,
    ):
        if api_key_anki:
            progress_anki = st.progress(0)
            status_anki = st.empty()

            def progress_anki_cb(pct, message):
                progress_anki.progress(pct / 100.0)
                status_anki.text(message)

            reservation = None
            started_anki = time.perf_counter()
            try:
                reservation = reserve_ai_usage(
                    SessionLocal,
                    user_id=st.session_state.get("user_id"),
                    provider=provider_key,
                    model="default",
                    task_type="anki_enrichment",
                    prompt="Lote de enriquecimiento Anki basado en preguntas existentes.",
                    planned_calls=max(run_count, 1),
                    prompt_version="anki-v1",
                )
                result = backfill_enrichments(
                    SessionLocal,
                    provider_key,
                    api_key_anki,
                    limit=int(batch_limit),
                    force=force_regeneration,
                    progress_callback=progress_anki_cb,
                )
                reservation.finish(
                    success=result["errors"] == 0,
                    completed_calls=max(result["total"], 1),
                    latency_ms=int((time.perf_counter() - started_anki) * 1000),
                )
                st.session_state["admin_anki_result"] = result
                st.rerun()
            except AIUsageLimitError as exc:
                st.warning(str(exc))
            except Exception as exc:
                log_ui_exception("admin.anki.enrichment", exc)
                if reservation is not None:
                    reservation.finish(
                        success=False,
                        latency_ms=int((time.perf_counter() - started_anki) * 1000),
                        error=exc,
                    )
                st.error("No fue posible preparar el lote en este momento.")
st.divider()
st.caption("🔒 Panel restringido a administradores.")
