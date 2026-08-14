import streamlit as st
import os, sys, pandas as pd
import datetime
from pathlib import Path
from sqlalchemy import Integer, func

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import (
    User, UserStats, UserOPEC, Attempt, Question, QuestionAnkiEnrichment,
    NormativaChunk,
)
from ui_utils import load_css, render_header
from core.access_control import require_admin
from core.normativa import NormativaManager
from core.anki_enrichment import backfill_enrichments
from core.admin_opec_assignment import AssignableOPECNotFound, assign_prepared_opec
from core.config import get_api_key

# pass # Removed st.set_page_config

require_admin()

load_css()
render_header(title="Panel de Control", subtitle="Estado de la app y gestión de usuarios")

tab_stats, tab_users, tab_technical = st.tabs([
    "📊 Estado general", "👥 Usuarios", "⚙️ Opciones técnicas"
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
                            assign_db, user_options[target_label], target_opec
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
                        st.error(f"No se pudo asignar la OPEC: {exc}")
                    finally:
                        assign_db.close()

    st.caption("🔒 Los roles, contraseñas y permisos no se modifican desde esta pantalla.")

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
        help="El texto extraído quedará guardado en la base de datos.",
    )
    if uploaded_file is not None:
        safe_name = Path(uploaded_file.name).name
        already_exists = (norm_path / safe_name).exists()
        if already_exists:
            st.warning(
                f"{safe_name} ya existe. Para evitar mezclar una versión anterior con otra nueva, "
                "cambia el nombre del archivo antes de cargarlo."
            )
        if st.button(
            "📥 Guardar y procesar PDF",
            type="primary",
            use_container_width=True,
            disabled=already_exists,
        ):
            (norm_path / safe_name).write_bytes(uploaded_file.getbuffer())
            manager = NormativaManager(str(norm_path))
            try:
                with st.spinner("Leyendo y preparando el documento..."):
                    indexed = manager.index_all()
                if indexed:
                    st.success(f"{safe_name} quedó listo: se agregaron {indexed} fragmentos nuevos.")
                else:
                    st.info(f"{safe_name} ya estaba procesado; no se encontraron fragmentos nuevos.")
                st.rerun()
            except Exception as e:
                st.error(f"No fue posible procesar el PDF: {e}")

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
            except Exception as e:
                st.error(f"Error indexando PDFs: {e}")
                
    with col_act2:
        missing_vectors = max(chunk_count - vector_count, 0)
        if st.button(
            f"🧠 Completar búsqueda semántica ({missing_vectors})",
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
                updated = manager.backfill_embeddings(progress_callback=progress_cb)
                st.success(f"Búsqueda semántica actualizada en {updated} fragmentos.")
                st.rerun()
            except Exception as e:
                st.error(f"Error generando embeddings: {e}")

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
        "Preguntas para preparar ahora", min_value=1, max_value=100, value=25, step=5,
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

            result = backfill_enrichments(
                SessionLocal,
                provider_key,
                api_key_anki,
                limit=int(batch_limit),
                force=force_regeneration,
                progress_callback=progress_anki_cb,
            )
            st.session_state["admin_anki_result"] = result
            st.rerun()
st.divider()
st.caption("🔒 Panel restringido a administradores.")
