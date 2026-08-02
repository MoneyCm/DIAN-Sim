import streamlit as st
import os, sys, pandas as pd
from pathlib import Path
from sqlalchemy import func

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
from core.config import get_api_key

# pass # Removed st.set_page_config

require_admin()

load_css()
render_header(title="Panel de administración", subtitle="Usuarios, banco y recursos normativos")

tab_stats, tab_users, tab_normativa, tab_anki = st.tabs(["📊 Estadísticas Globales", "👥 Gestión de Usuarios", "🏛️ Inteligencia Normativa", "🎴 Enriquecimiento Anki"])

# --- TAB: STATS ---
with tab_stats:
    db = SessionLocal()
    total_users = db.query(User).count()
    total_attempts = db.query(Attempt).count()
    total_points = db.query(func.sum(UserStats.total_points)).scalar() or 0
    total_questions = db.query(Question).count()
    db.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Usuarios Totales", total_users)
    with col2:
        st.metric("Simulacros Realizados", total_attempts)
    with col3:
        st.metric("Puntos Globales", f"{total_points:,}")
    with col4:
        st.metric("Banco de Preguntas", total_questions)

    st.divider()
    st.subheader("Uso del Sistema")
    # Here we could add a plot of usage over time if needed.
    st.info("Estas cifras son globales y abarcan todos los concursos registrados.")

# --- TAB: USERS ---
with tab_users:
    db = SessionLocal()
    users = db.query(User).all()
    user_data = []
    for u in users:
        stats = db.query(UserStats).filter_by(user_id=u.id).first()
        opecs = db.query(UserOPEC).filter_by(user_id=u.id).count()
        user_data.append({
            "ID": u.id,
            "Usuario": u.username,
            "Rol": u.role,
            "Puntos": stats.total_points if stats else 0,
            "Cargos (OPECs)": opecs,
            "Fecha Registro": u.created_at.strftime("%Y-%m-%d") if u.created_at else "N/A"
        })
    db.close()
    
    df_users = pd.DataFrame(user_data)
    st.dataframe(df_users, use_container_width=True)
    
    st.caption("La modificación de roles no está disponible desde esta pantalla.")

# --- TAB: NORMATIVA ---
with tab_normativa:
    st.subheader("📚 Biblioteca normativa")
    st.caption(
        "Aquí se prepara el material legal que usa la búsqueda de fuentes del generador. "
        "Esta sección no modifica el banco de preguntas automáticamente."
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
    st.subheader("🧠 Material de repaso explicado")
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
