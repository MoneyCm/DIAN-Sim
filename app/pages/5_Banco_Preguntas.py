import streamlit as st
import pandas as pd
import os, sys, uuid, datetime, io, time

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import Question
from core.dedupe import compute_hash, find_duplicates
from core.import_utils import validate_import_df
from core.generators.llm import LLMGenerator
from core.config import get_api_key
from ui_utils import load_css, render_header, render_custom_sidebar

from core.auth import AuthManager
from core.competitions import get_active_competition_id
from core.exam_format import (
    OFFICIAL_LABEL, PRACTICE_LABEL, REVIEW_LABEL, question_format_status,
)
from core.question_review import (
    approve_candidate, candidate_validation_error, is_reinforcement_candidate,
    record_ai_audit, reject_candidate,
)

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión.")
    st.stop()

load_css()
render_header(title="SISC de Preguntas (Pro)", subtitle="Gestión avanzada, carga masiva y control de calidad")

# --- INITIALIZATION ---
if "bulk_selection" not in st.session_state:
    st.session_state["bulk_selection"] = set()
if "page_num" not in st.session_state:
    st.session_state["page_num"] = 1

def reset_selection():
    st.session_state["bulk_selection"] = set()
    # Clear individual checkbox keys Mikey v36
    for key in list(st.session_state.keys()):
        if key.startswith("sel_"):
            st.session_state[key] = False

# --- SIDEBAR TOOLS ---
stats_s, rank = render_custom_sidebar()

with st.sidebar:
    st.divider()
    st.markdown("### 🛠️ Herramientas Pro")
    if st.button("🗑️ Limpiar Selección"):
        reset_selection()
        st.rerun()
    
    st.caption("Paginación")
    cols_page = st.columns(2)
    if cols_page[0].button("⬅️ Ant."):
        st.session_state["page_num"] = max(1, st.session_state["page_num"] - 1)
        st.rerun()
    if cols_page[1].button("Sig. ➡️"):
        st.session_state["page_num"] += 1
        st.rerun()

action = st.radio("Acción", ["Explorar / Bulk", "Carga Masiva (Excel/CSV)", "Crear Manualmente"], horizontal=True)
st.divider()

db = SessionLocal()

# OPEC Focus Toggle Mikey v6.4
u_id = st.session_state.get("user_id")
from services.question_service import QuestionService

# Detect if user has active OPEC to set default
from db.models import UserOPEC
has_opec = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first() is not None

opec_focus = st.toggle("🎯 Enfoque por mi OPEC (Alta Precisión)", 
                       value=has_opec, 
                       help="Muestra solo preguntas que coinciden con las funciones y naturaleza de tu cargo configurado.")

if action == "Explorar / Bulk":
    # FILTERS
    col_filters = st.columns([2, 1, 1, 1, 1, 1])
    with col_filters[0]:
        search = st.text_input("🔍 Buscar en enunciado o justificación...")
    with col_filters[1]:
        track_f = st.selectbox("Eje", ["Todos", "FUNCIONAL", "COMPORTAMENTAL", "INTEGRIDAD"])
    with col_filters[2]:
        diff_f = st.multiselect("Dificultad", [1, 2, 3], format_func=lambda x: {1: "🟢 Básico", 2: "🟡 Intermedio", 3: "🔴 Avanzado"}[x])
    with col_filters[3]:
        # Quality Filter Mikey v36
        quality_f = st.selectbox("Calidad", ["Todas", "Solo Verificadas ✅", "Pendientes ⏳"])
    with col_filters[4]:
        format_f = st.selectbox("Formato", ["Todos", OFFICIAL_LABEL, PRACTICE_LABEL, REVIEW_LABEL])
    with col_filters[5]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state["bulk_selection"]:
            st.markdown(f"### ⚙️ Acciones Masivas ({len(st.session_state['bulk_selection'])} ítems seleccionados)")
            col_audit, col_del_real = st.columns([1, 1])
            
            with col_audit:
                # v34.1 Bulk Audit Button Mikey
                if st.button(f"🛡️ Auditar Selección", type="primary", use_container_width=True, help="Certifica la calidad de todas las preguntas seleccionadas."):
                    try:
                        provider = st.session_state.get("current_provider", "Gemini")
                        api_key = get_api_key(provider)
                        if api_key:
                            gen = LLMGenerator(provider, api_key)
                            if not hasattr(gen, 'audit_question'):
                                st.warning("⏳ Esperando actualización del servidor. Reintenta en 30s.")
                            else:
                                prog_audit = st.progress(0, text="Iniciando Auditoría Masiva...")
                                selection = list(st.session_state["bulk_selection"])
                                for i, qid in enumerate(selection):
                                    prog_audit.progress((i + 1) / len(selection), text=f"Auditando {i+1} de {len(selection)}...")
                                    q_aud = db.query(Question).get(qid)
                                    if q_aud and not q_aud.is_verified:
                                        report = gen.audit_question({
                                            "topic": q_aud.topic, "stem": q_aud.stem, 
                                            "options_json": q_aud.options_json, 
                                            "correct_key": q_aud.correct_key, 
                                            "rationale": q_aud.rationale
                                        })
                                        record_ai_audit(q_aud, report)
                                        # El dictamen de IA se conserva como ayuda; la aprobación
                                        # para estudiar requiere comprobación normativa separada.
                                    
                                    # Delay to avoid 429 Rate Limit Mikey v39
                                    time.sleep(1.5) 
                                db.commit()
                                st.success("¡Auditoría masiva completada!")
                                st.rerun()
                        else:
                            st.error("Falta API Key")
                    except Exception as e:
                        db.rollback()
                        st.error(f"Error en auditoría masiva: {e}")

            with col_del_real:
                if st.button(f"🗑️ Borrar Selección", type="secondary", use_container_width=True):
                    try:
                        for qid in st.session_state["bulk_selection"]:
                            q_to_del = db.query(Question).get(qid)
                            if q_to_del: db.delete(q_to_del)
                        db.commit()
                        reset_selection()
                        st.success("Preguntas eliminadas.")
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"Error: {e}")
            
            st.divider()
            
            # Export Logic
            selected_qs = db.query(Question).filter(Question.question_id.in_(list(st.session_state["bulk_selection"]))).all()
            
            if selected_qs:
                st.markdown("### 📥 Exportar Seleccionadas")
                col_down_ex, col_down_txt = st.columns([1, 1])
                
                # 1. Excel Export
                export_data = []
                for q in selected_qs:
                    opts = q.options_json if q.options_json else {}
                    export_data.append({
                        'track': q.track,
                        'competency': q.competency,
                        'topic': q.topic,
                        'difficulty': q.difficulty,
                        'stem': q.stem,
                        'options_A': opts.get('A', ''),
                        'options_B': opts.get('B', ''),
                        'options_C': opts.get('C', ''),
                        'options_D': opts.get('D', ''),
                        'correct_key': q.correct_key,
                        'rationale': q.rationale
                    })
                df_exp = pd.DataFrame(export_data)
                topo_ex = io.BytesIO()
                with pd.ExcelWriter(topo_ex, engine='openpyxl') as writer:
                    df_exp.to_excel(writer, index=False)
                
                with col_down_ex:
                    st.download_button(
                        "📥 Descargar Excel",
                        data=topo_ex.getvalue(),
                        file_name=f"Seleccion_Preguntas_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                # 2. Text Export
                lines = ["track|competency|topic|stem|options_A|options_B|options_C|options_D|correct_key|rationale|difficulty"]
                for d in export_data:
                    line = "|".join([
                        str(d['track']), str(d['competency']), str(d['topic']), 
                        str(d['stem']).replace("\n", " "), 
                        str(d['options_A']), str(d['options_B']), str(d['options_C']), str(d['options_D']),
                        str(d['correct_key']), str(d['rationale']).replace("\n", " "), str(d['difficulty'])
                    ])
                    lines.append(line)
                
                with col_down_txt:
                    st.download_button(
                        "📄 Descargar Texto (|)",
                        data="\n".join(lines),
                        file_name=f"Seleccion_Preguntas_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

    # QUERY
    if opec_focus:
        # Usamos el servicio de alta precisión
        questions_all = QuestionService.get_questions_for_user(db, u_id, include_review=True)
        # Aplicamos filtros de UI sobre el set filtrado por OPEC (Filtrado en memoria Python)
        filtered = []
        for q in questions_all:
            if search and not (search.lower() in (q.stem + (q.rationale or "")).lower()):
                continue
            if track_f != "Todos" and q.track != track_f:
                continue
            if diff_f and q.difficulty not in diff_f:
                continue
            if quality_f == "Solo Verificadas ✅" and not q.is_verified:
                continue
            if quality_f == "Pendientes ⏳" and q.is_verified:
                continue
            if format_f != "Todos" and question_format_status(q) != format_f:
                continue
            filtered.append(q)
        
        total_count = len(filtered)
        PAGE_SIZE = 20
        offset = (st.session_state["page_num"] - 1) * PAGE_SIZE
        questions = filtered[offset:offset+PAGE_SIZE]
        st.info(f"🎯 **Enfoque OPEC:** Filtrando **{total_count}** preguntas pertinentes para tu cargo.")
    else:
        # Búsqueda global estándar (SQL)
        query = db.query(Question)
        if search:
            query = query.filter(Question.stem.ilike(f"%{search}%") | Question.rationale.ilike(f"%{search}%"))
        if track_f != "Todos":
            query = query.filter(Question.track == track_f)
        if diff_f:
            query = query.filter(Question.difficulty.in_(diff_f))
        
        if quality_f == "Solo Verificadas ✅":
            query = query.filter(Question.is_verified == True)
        elif quality_f == "Pendientes ⏳":
            query = query.filter(Question.is_verified == False)
        
        filtered = query.all()
        if format_f != "Todos":
            filtered = [q for q in filtered if question_format_status(q) == format_f]
        total_count = len(filtered)
        PAGE_SIZE = 20
        offset = (st.session_state["page_num"] - 1) * PAGE_SIZE
        questions = filtered[offset:offset+PAGE_SIZE]
        st.info(f"📚 Mostrando **{len(questions)}** de **{total_count}** preguntas totales.")
    
    if not questions:
        st.warning("No hay preguntas que coincidan con la búsqueda.")
    else:
        # SELECT ALL / UNSELECT ALL BUTTONS v36 Mikey
        col_m_sel, col_m_unsel = st.columns([1, 1])
        with col_m_sel:
            if st.button("✅ Seleccionar todas las visibles", use_container_width=True):
                for q in questions:
                    st.session_state["bulk_selection"].add(q.question_id)
                    st.session_state[f"sel_{q.question_id}"] = True # Force sync Mikey
                st.rerun()
        with col_m_unsel:
            if st.button("❌ Deseleccionar visibles", use_container_width=True):
                for q in questions:
                    st.session_state["bulk_selection"].discard(q.question_id)
                    st.session_state[f"sel_{q.question_id}"] = False # Force sync Mikey
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        for q in questions:
            diff_tags = {1: "🟢", 2: "🟡", 3: "🔴"}
            is_selected = q.question_id in st.session_state["bulk_selection"]
            
            # Use small columns for the selection logic
            col_sel, col_exp = st.columns([0.05, 0.95])
            
            with col_sel:
                if st.checkbox("Seleccionar", value=is_selected, key=f"sel_{q.question_id}", label_visibility="collapsed"):
                    st.session_state["bulk_selection"].add(q.question_id)
                else:
                    st.session_state["bulk_selection"].discard(q.question_id)
            
            with col_exp:
                status_icon = "✅" if getattr(q, 'is_verified', False) else "⏳"
                format_status = question_format_status(q)
                format_icon = "OFICIAL" if format_status == OFFICIAL_LABEL else "PRACTICA" if format_status == PRACTICE_LABEL else "REVISAR"
                display_title = f"{status_icon} {format_icon} {diff_tags.get(q.difficulty, '⚪')} [{q.track or 'SIN EJE'}] {q.stem[:80]}..."
                with st.expander(display_title):
                    st.caption(f"Formato: {format_status}")
                    st.markdown(f"**Enunciado:**\n{q.stem}")
                    ops = q.options_json if q.options_json else {}
                    if ops:
                        cols_ops = st.columns(2)
                        for i, (key, val) in enumerate(ops.items()):
                            cols_ops[i % 2].markdown(f"**{key})** {val}")
                    
                    st.markdown(f"**Respuesta Correcta:** :green[{q.correct_key}]")
                    if q.rationale:
                        st.caption(f"Justificación: {q.rationale}")
                    if q.source_refs:
                        st.caption(f"Fuente: {q.source_refs}")

                    if is_reinforcement_candidate(q):
                        st.warning("Refuerzo generado por IA: pendiente de comprobación normativa.")
                        validation_error = candidate_validation_error(q)
                        if validation_error:
                            st.error(validation_error)
                        elif AuthManager.is_admin():
                            confirmation = st.checkbox(
                                "Revisé el enunciado, la clave, la justificación y la fuente.",
                                key=f"confirm_candidate_{q.question_id}",
                            )
                            approve_col, reject_col = st.columns(2)
                            if approve_col.button(
                                "✅ Aprobar para práctica",
                                key=f"approve_candidate_{q.question_id}",
                                disabled=not confirmation,
                                use_container_width=True,
                            ):
                                approve_candidate(q, st.session_state.get("username", "admin"))
                                db.commit()
                                st.success("Refuerzo aprobado. Ya puede entrar en la práctica activa.")
                                st.rerun()
                            if reject_col.button(
                                "⛔ Descartar candidato",
                                key=f"reject_candidate_{q.question_id}",
                                use_container_width=True,
                            ):
                                reject_candidate(q, st.session_state.get("username", "admin"))
                                db.commit()
                                st.success("Candidato descartado y conservado para trazabilidad.")
                                st.rerun()
                        else:
                            st.info("Solo un administrador puede aprobar o descartar este candidato.")
                    
                    st.divider()
                    col_act1, col_act2, col_act3 = st.columns([1, 1, 1])
                    
                    with col_act1:
                        if st.button("🛡️ Auditar con IA", key=f"audit_{q.question_id}", use_container_width=True):
                            with st.spinner("Realizando auditoría técnica..."):
                                try:
                                    provider = st.session_state.get("current_provider", "Gemini")
                                    api_key = get_api_key(provider)
                                    if api_key:
                                        gen = LLMGenerator(provider, api_key)
                                        
                                        # Resilient Attribute Check Mikey v33
                                        if hasattr(gen, 'audit_question'):
                                            report = gen.audit_question({
                                                "topic": q.topic, "stem": q.stem, 
                                                "options_json": q.options_json, 
                                                "correct_key": q.correct_key, 
                                                "rationale": q.rationale
                                            })
                                            record_ai_audit(q, report)
                                            # La IA orienta la revisión, pero no habilita por sí
                                            # sola una pregunta para el estudio activo.
                                            db.commit()
                                            st.success(f"Auditoría completada: {report.get('score')}/10")
                                            st.rerun()
                                        else:
                                            st.warning("⏳ El servidor está actualizando el motor de IA. Por favor, espera 30 segundos y vuelve a intentar. Mikey")
                                    else:
                                        st.error("Falta API Key")
                                except Exception as e:
                                    st.error(f"Error: {e}")

                    with col_act2:
                        if st.button("🗑️ Eliminar", key=f"del_single_{q.question_id}", type="secondary", use_container_width=True):
                            db.delete(q)
                            db.commit()
                            st.rerun()
                            
                    with col_act3:
                        # Psychometric Insight Mikey
                        hits = getattr(q, 'global_hits', 0)
                        misses = getattr(q, 'global_misses', 0)
                        total = hits + misses
                        disc_idx = (hits / total * 100) if total > 0 else 0
                        st.caption(f"⚡ Índice de Acierto Global: {disc_idx:.0f}%")
                    
                    if getattr(q, 'quality_report', None):
                        with st.expander("📄 Ver Reporte de Auditoría", expanded=False):
                            rep = q.quality_report
                            ai_rep = rep.get("ai_audit") if isinstance(rep.get("ai_audit"), dict) else rep
                            score = ai_rep.get("score", "Sin calificar")
                            st.markdown(f"**Score IA:** {score}/10 | **Estado de control:** {rep.get('status')}")
                            st.write(f"**Crítica:** {ai_rep.get('critique', 'Sin observaciones')}")
                            st.write("**Hallazgos:**")
                            for f in ai_rep.get('findings', []):
                                st.write(f"- {f}")
                            st.info(f"💡 **Sugerencia:** {ai_rep.get('suggestion', 'Sin sugerencias')}")

elif action == "Carga Masiva (Excel/CSV)":
    st.info("Sube un archivo `.xlsx` o `.csv`. Columnas requeridas: `track, competency, topic, stem, options_A, options_B, options_C, options_D, correct_key, rationale` (opcional)")
    
    # --- TEMPLATE DOWNLOAD ---
    template_data = {
        'track': ['FUNCIONAL', 'COMPORTAMENTAL', 'INTEGRIDAD'],
        'competency': ['Gestión Tributaria', 'Orientación al Logro', 'Ética'],
        'topic': ['IVA', 'Trabajo en Equipo', 'Valores'],
        'stem': ['SITUACIÓN: Un contribuyente... PREGUNTA: ¿Qué hacer?', 'SITUACIÓN: Caso de equipo...', 'SITUACIÓN: Dilema ético...'],
        'options_A': ['Opción 1', 'Valor 1', 'Acción 1'],
        'options_B': ['Opción 2', 'Valor 2', 'Acción 2'],
        'options_C': ['Opción 3', 'Valor 3', 'Acción 3'],
        'options_D': ['Opción 4', 'Valor 4', 'Acción 4'],
        'correct_key': ['A', 'B', 'C'],
        'rationale': ['Explicación A', 'Explicación B', 'Explicación C'],
        'difficulty': [2, 1, 3]
    }
    df_template = pd.DataFrame(template_data)
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
        df_template.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Descargar Plantilla Excel (.xlsx)",
        data=towrite.getvalue(),
        file_name="Plantilla_Preguntas_DIAN.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    st.divider()
    
    uploaded = st.file_uploader("Archivo de preguntas", type=["csv", "xlsx"])
    
    if uploaded:
        try:
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            
            st.success(f"Archivo leído: {len(df)} filas detectadas.")
            
            # VALIDATION
            is_valid, err_list = validate_import_df(df)
            
            if not is_valid:
                st.error("📉 El archivo tiene errores de estructura o datos:")
                for err in err_list[:15]: # Limit display
                    st.write(f"- {err}")
                if len(err_list) > 15:
                    st.write(f"... y {len(err_list)-15} errores más.")
                st.stop()
            else:
                st.success("✅ Estructura validada correctamente.")
                with st.expander("Previsualizar datos"):
                    st.dataframe(df.head())
                
                if st.button("🚀 Procesar e Importar", type="primary"):
                    count_ok = 0
                    count_dupe = 0
                    
                    existing_hashes = [q.hash_norm for q in db.query(Question.hash_norm).all()]
                    
                    progress = st.progress(0)
                    for index, row in df.iterrows():
                        progress.progress((index + 1) / len(df))
                        stem = str(row['stem'])
                        h = compute_hash(stem)
                        
                        if h in existing_hashes:
                            count_dupe += 1
                            continue
                            
                        ops = {
                            "A": str(row['options_A']),
                            "B": str(row['options_B']),
                            "C": str(row['options_C']),
                            "D": str(row['options_D'])
                        }
                        
                        # Safe difficulty conversion
                        raw_diff = row.get('difficulty', 2)
                        try:
                            difficulty = int(float(raw_diff)) if not pd.isna(raw_diff) else 2
                        except (ValueError, TypeError):
                            difficulty = 2
                            
                        q = Question(
                            competition_id=get_active_competition_id(db, u_id),
                            question_id=str(uuid.uuid4()),
                            track=str(row['track']).upper(),
                            competency=str(row.get('competency', 'General')),
                            topic=str(row.get('topic', 'General')),
                            difficulty=difficulty,
                            stem=stem,
                            options_json=ops,
                            correct_key=str(row['correct_key']).strip().upper(),
                            rationale=str(row.get('rationale', '')),
                            hash_norm=h
                        )
                        db.add(q)
                        count_ok += 1
                        existing_hashes.append(h) # Update local cache for batch
                    
                    db.commit()
                    st.balloons()
                    st.success(f"¡Importación Finalizada! Nuevas: {count_ok} | Duplicadas omitidas: {count_dupe}")

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

elif action == "Crear Manualmente":
    with st.form("manual_create"):
        st.subheader("Nueva Pregunta")
        col1, col2 = st.columns(2)
        with col1:
            track = st.selectbox("Track / Eje", ["FUNCIONAL", "COMPORTAMENTAL", "INTEGRIDAD"])
            topic = st.text_input("Tema")
        with col2:
            stem = st.text_area("Enunciado de la Pregunta")
            difficulty = st.select_slider("Dificultad", options=[1, 2, 3], format_func=lambda x: {1: "Básico", 2: "Intermedio", 3: "Avanzado"}[x], value=2)
            
        st.markdown("---")
        st.markdown("**Opciones de Respuesta**")
        c1, c2 = st.columns(2)
        with c1:
            op_a = st.text_input("Opción A")
            op_b = st.text_input("Opción B")
        with c2:
            op_c = st.text_input("Opción C")
            op_d = st.text_input("Opción D")
            
        col_correct, col_rationale = st.columns([1, 2])
        with col_correct:
            correct = st.selectbox("Respuesta Correcta", ["A", "B", "C", "D"])
        with col_rationale:
            rationale = st.text_area("Justificación / Explicación")
        
        if st.form_submit_button("Guardar Pregunta", type="primary"):
            h = compute_hash(stem)
            if db.query(Question).filter_by(hash_norm=h).first():
                st.error("¡Pregunta idéntica ya existe!")
            else:
                q = Question(
                    competition_id=get_active_competition_id(db, u_id),
                    question_id=str(uuid.uuid4()),
                    track=track,
                    competency="Manual",
                    topic=topic,
                    stem=stem,
                    difficulty=difficulty,
                    options_json={"A": op_a, "B": op_b, "C": op_c, "D": op_d},
                    correct_key=correct,
                    rationale=rationale,
                    hash_norm=h
                )
                db.add(q)
                db.commit()
                st.success("Pregunta guardada exitosamente.")

db.close()
