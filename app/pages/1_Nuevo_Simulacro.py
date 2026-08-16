import streamlit as st
import os, sys, time
from collections import Counter

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
import pandas as pd

from db.session import SessionLocal
from sqlalchemy import inspect

from db.models import (
    ErrorEpisode,
    OpecLearningEvent,
    OpecLearningSession,
    Question,
    Skill,
    UserOPEC,
)
from core.adaptive import select_questions_for_simulation
from core.exam_format import OFFICIAL_LABEL, question_format_status
from core.opec_question_context import (
    function_number_for_question,
    matches_manual_function_filter,
)
from core.learning.difficulty import difficulty_label
from core.learning.engine import editorial_question_difficulty
from core.diagnostic import DiagnosticCandidate, DiagnosticPolicy, select_diagnostic
from core.learning.evidence_service import ensure_question_revision
from core.practice_modes import (
    MODE_COMPETENCY,
    MODE_ERRORS,
    MODE_FULL,
    MODE_FUNCTION,
    MODE_MAXIMUM,
    MODE_PARTIAL,
    MODE_RECOMMENDED,
    MODE_TOPIC,
    STRICT_COMPLETENESS_MODES,
    select_practice_questions,
)
from core.simulation_policy import (
    SimulationPolicyValidationError,
    resolve_simulation_policy,
)
from core.simulation_policy_store import (
    SimulationPolicyStoreError,
    load_active_simulation_policy,
)
from services.question_service import QuestionService
from ui_utils import load_css, log_ui_exception, render_header
from core.profiles import PROFILES, get_profile_topics

def get_db():
    return SessionLocal()

from core.auth import AuthManager
from core.competitions import get_active_competition_id


PRACTICE_MODE_LABELS = {
    "Recomendada adaptativa": MODE_RECOMMENDED,
    "Corta por tema": MODE_TOPIC,
    "Por competencia": MODE_COMPETENCY,
    "Por función del manual": MODE_FUNCTION,
    "Parcial PJS de entrenamiento": MODE_PARTIAL,
    "Completa de entrenamiento": MODE_FULL,
    "Transferencia de errores": MODE_ERRORS,
    "Máxima exigencia": MODE_MAXIMUM,
}

# UI Setup
# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión en la página principal.")
    st.stop()

# UI Setup
load_css()
render_header(title="Práctica personalizada", subtitle="Elige una sesión breve y enfócate en una habilidad")

with st.container():
    st.markdown('<div class="dian-card">', unsafe_allow_html=True)
    
    # Tabs for Mode
    tab_opec, tab_manual, tab_profile = st.tabs([
        "✨ Práctica recomendada", "⚙️ Personalizar", "🧭 Otro cargo",
    ])
    
    with tab_manual:
        with st.form("manual_sim_form"):
            st.markdown("### Configuración rápida")
            st.markdown("**Duración de la práctica**")
            num_questions = st.select_slider(
                "Cantidad de preguntas", options=[5, 10, 15, 20], value=10,
                format_func=lambda value: f"{value} preguntas · aprox. {max(8, value * 2)} min",
                key="num_q_manual",
            )
            
            st.markdown("<br>**Filtros opcionales** (Dejar vacío para incluir todo)", unsafe_allow_html=True)
            
            # Get available options with error handling
            try:
                db_temp = get_db()
                competition_id = get_active_competition_id(db_temp, st.session_state.get("user_id"))
                competition_questions = QuestionService.get_questions_for_user(
                    db_temp,
                    st.session_state.get("user_id"),
                    competition_id=competition_id,
                )
                all_tracks = sorted({question.track for question in competition_questions if question.track})
                all_competencies = sorted({question.competency for question in competition_questions if question.competency})
                all_topics = sorted({question.topic for question in competition_questions if question.topic})
                db_temp.close()
            except Exception as e:
                log_ui_exception("practice.filters.load", e)
                st.error("No fue posible consultar el banco de preguntas.")
                st.info("Intenta recargar la página o verifica tu conexión a internet.")
                all_tracks, all_competencies, all_topics = [], [], []

            col1, col2 = st.columns(2)
            with col1:
                track_filter = st.multiselect(
                    "Área del banco",
                    sorted(all_tracks),
                    placeholder="Todas las áreas",
                    help="Clasificación interna de práctica; no corresponde a ejes oficiales aún no publicados.",
                )
                difficulty_filter = st.multiselect(
                    "Dificultad editorial interna", list(range(1, 11)), placeholder="Todos los niveles",
                    format_func=lambda value: f"Nivel {value} · {difficulty_label(value)}",
                    help="Escala interna 1–10; no es una clasificación oficial de la CNSC.",
                )
            with col2:
                competency_filter = st.multiselect(
                    "Competencia", sorted(all_competencies), placeholder="Todas las competencias"
                )
            
            recommended_topic = st.session_state.get("practice_recommended_topic")
            default_topics = [recommended_topic] if recommended_topic in all_topics else []
            topic_filter = st.multiselect(
                "Tema específico", sorted(all_topics), default=default_topics,
                placeholder="Todos los temas"
            )
            if default_topics:
                    st.caption(f"Recomendación aplicada desde tus resultados: {recommended_topic}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            only_situational_manual = st.toggle(
                "Usar preguntas situacionales", value=True,
                help="Incluye casos laborales para entrenar análisis y toma de decisiones.",
                key="only_sit_manual",
            )
            hardcore_mode = False
            st.caption(
                "Para práctica PJS cronometrada e índice interno usa **Práctica PJS cronometrada**. "
                "La cantidad, duración y ponderación oficiales siguen pendientes de publicación."
            )
            
            submitted_manual = st.form_submit_button("▶️ Iniciar práctica", type="primary", use_container_width=True)
            st.caption("Sugerencia de foco: comienza con 10 preguntas y sube gradualmente.")

    # --- PROFILE MODE ---
    with tab_profile:
        st.info("Selecciona el cargo al que aspiras para enfocar el estudio en sus funciones y competencias específicas.")
        
        selected_profile_name = st.selectbox("Seleccionar Cargo / Perfil", list(PROFILES.keys()))
        available_count = 0
        if selected_profile_name:
            profile_data = PROFILES[selected_profile_name]
            st.markdown(f"**Descripción:** {profile_data['description']}")
            
            profile_topics = get_profile_topics(selected_profile_name)
            
            with st.expander("Ver Temas y Competencias del Perfil", expanded=False):
                st.write("**Temas Funcionales:**")
                st.write(", ".join(profile_data["functional_tracks"].get("FUNCIONAL", [])))
                st.write("**Competencias Comportamentales:**")
                st.write(", ".join(profile_data["behavioral_competencies"]))
            
            st.markdown("---")
            col_p1, col_p2 = st.columns([1, 1])
            with col_p1:
                num_questions_profile = st.select_slider(
                    "Cantidad de preguntas", options=[5, 10, 15, 20], value=10,
                    key="num_q_profile",
                )
            with col_p2:
                difficulty_profile = st.multiselect(
                    "Dificultad editorial interna",
                    list(range(1, 11)),
                    default=list(range(1, 11)),
                    format_func=lambda value: f"Nivel {value} · {difficulty_label(value)}",
                    key="diff_profile",
                    help="Escala interna 1–10; no es una clasificación oficial de la CNSC.",
                )

            # Check availability
            try:
                db_chk = get_db()
                profile_candidates = QuestionService.get_questions_for_user(
                    db_chk, st.session_state.get("user_id")
                )
                available_count = sum(
                    question.topic in profile_topics
                    and (
                        not difficulty_profile
                        or editorial_question_difficulty(question) in difficulty_profile
                    )
                    for question in profile_candidates
                )
                db_chk.close()
                
                if available_count < 5:
                    st.warning(f"⚠️ Solo hay {available_count} preguntas disponibles para estos temas en tu banco local.")
                    if AuthManager.is_admin():
                        with st.expander("Opciones para cubrir la brecha", expanded=False):
                            if st.button("Crear candidatos para cubrir la brecha"):
                                st.session_state["ai_default_text"] = profile_data["raw_text"]
                                st.session_state["ai_default_topic"] = selected_profile_name
                                st.session_state["ai_default_diff"] = difficulty_profile[0] if len(difficulty_profile) == 1 else 2
                                st.switch_page("pages/4_Generador_IA.py")
                    else:
                        st.info("La brecha fue identificada. Continúa con los temas disponibles mientras el banco se amplía y revisa.")
                else:
                    st.success(f"✅ Hay {available_count} preguntas disponibles para este perfil.")
            except Exception as e:
                st.error("⚠️ Error al consultar el banco. Es posible que la base de datos se esté actualizando.")
                available_count = 0
        
        st.markdown("### Lanzar práctica del perfil")
        st.markdown("---")
        only_situational = st.toggle("Solo preguntas situacionales (Nuevas)", value=True, help="Filtra para mostrar solo preguntas que plantean casos prácticos generados con el nuevo sistema.")

        if st.button("▶️ Iniciar práctica por cargo", type="primary", disabled=(available_count == 0)):
             submitted_profile = True
        else:
             submitted_profile = False

    # --- OPEC MODE (NEW Fase 2) ---
    with tab_opec:
        db_opec = get_db()
        u_id = st.session_state.get("user_id")
        active_opec = db_opec.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
        opec_simulation_policy = None
        opec_policy_error = None
        opec_mode_candidates = (
            QuestionService.get_questions_for_user(
                db_opec,
                u_id,
                competition_id=active_opec.competition_id,
                user_opec=active_opec,
                bank_partitions=("training",),
            )
            if active_opec is not None
            else []
        )
        if active_opec is not None:
            try:
                _, _, opec_simulation_policy = load_active_simulation_policy(
                    db_opec,
                    competition_id=active_opec.competition_id,
                    opec_number=active_opec.opec_number,
                )
            except SimulationPolicyStoreError:
                opec_simulation_policy = resolve_simulation_policy(
                    None,
                    opec_number=active_opec.opec_number,
                    function_count=len(active_opec.functions or ()),
                )
            except SimulationPolicyValidationError as exc:
                opec_policy_error = str(exc)
        db_opec.close()
        
        if active_opec:
            st.success(f"🎯 **Meta actual:** {active_opec.job_title} (OPEC {active_opec.opec_number})")
            if opec_policy_error:
                st.error(
                    "La política versionada de práctica requiere corrección administrativa: "
                    f"{opec_policy_error}"
                )
                st.stop()
            st.markdown(f"**Propósito:** {active_opec.purpose}")
            
            with st.expander("Ver Manual de Funciones", expanded=False):
                if active_opec.functions:
                    for f in active_opec.functions:
                        st.write(f"- {f}")
            
            st.divider()
            st.markdown("### Diagnóstico inicial")
            st.caption(
                "Mide una línea base con preguntas nuevas y una muestra de cada una de las nueve "
                "funciones. Solo se habilita si el banco confiable permite una cobertura completa; "
                "una muestra parcial no se presenta como diagnóstico."
            )
            if st.button(
                "🧭 Preparar diagnóstico de 9 funciones",
                use_container_width=True,
                key="start_opec_diagnostic",
            ):
                st.session_state["diagnostic_run"] = True
                st.session_state.pop("diagnostic_gaps", None)
                st.rerun()
            if st.session_state.get("diagnostic_gaps"):
                st.warning("El diagnóstico aún no puede ser completo.")
                st.markdown("\n".join(
                    f"- F{item['function_number']}: faltan {item['missing']} pregunta(s) confiable(s)."
                    for item in st.session_state["diagnostic_gaps"]
                ))

            st.markdown("### Práctica para la OPEC")
            st.info(
                "📈 **Progresión interna 1–10:** cada tema nuevo comienza en nivel 1. "
                "El ascenso exige una muestra mínima, aciertos en preguntas nuevas, retención diferida "
                "y desempeño de medición; nunca ocurre por unos pocos aciertos. Los errores reiterados "
                "ajustan solo ese tema. Es una política pedagógica propia, no una escala de la CNSC."
            )
            selected_mode_label = st.selectbox(
                "Tipo de práctica",
                list(PRACTICE_MODE_LABELS),
                help=(
                    "Las prácticas usan el banco de entrenamiento. La medición estricta, "
                    "sin ayudas y con material reservado, se inicia en Práctica PJS cronometrada."
                ),
                key="opec_practice_mode_label",
            )
            selected_opec_mode = PRACTICE_MODE_LABELS[selected_mode_label]
            function_options = {
                f"F{index}. {' '.join(str(function).split())[:105]}": index
                for index, function in enumerate(active_opec.functions or [], start=1)
            }
            available_opec_topics = sorted(
                {question.topic for question in opec_mode_candidates if question.topic}
            )
            available_opec_competencies = sorted(
                {
                    question.competency
                    for question in opec_mode_candidates
                    if question.competency
                }
            )
            selected_mode_topics = []
            selected_mode_competencies = []
            selected_mode_functions = []
            if selected_opec_mode == MODE_TOPIC:
                selected_mode_topics = [
                    st.selectbox("Tema", available_opec_topics)
                ] if available_opec_topics else []
            elif selected_opec_mode == MODE_COMPETENCY:
                selected_mode_competencies = [
                    st.selectbox("Competencia", available_opec_competencies)
                ] if available_opec_competencies else []
            elif selected_opec_mode == MODE_FUNCTION:
                selected_label = (
                    st.selectbox("Función del manual", list(function_options))
                    if function_options
                    else None
                )
                selected_mode_functions = [function_options[selected_label]] if selected_label else []

            fixed_sizes = {
                MODE_PARTIAL: opec_simulation_policy.internal.mode("partial").question_count,
                MODE_FULL: opec_simulation_policy.internal.mode("full").question_count,
                MODE_ERRORS: 10,
                MODE_MAXIMUM: 15,
            }
            if selected_opec_mode in fixed_sizes:
                num_q_opec = fixed_sizes[selected_opec_mode]
                st.caption(
                    f"Configuración interna {opec_simulation_policy.policy_version}: "
                    f"{num_q_opec} preguntas. La cantidad oficial por cuadernillo "
                    "sigue pendiente."
                )
            else:
                num_q_opec = st.select_slider(
                    "Tamaño de la práctica",
                    options=[5, 10, 15, 20],
                    value=10,
                    format_func=lambda value: (
                        f"{value} preguntas · aprox. {max(8, value * 2)} min"
                    ),
                    key="num_opec_q_input",
                )
            if selected_opec_mode == MODE_ERRORS:
                st.caption(
                    "Usa preguntas diferentes pero relacionadas con errores abiertos; "
                    "no repite la misma pregunta para simular una mejora."
                )
            if selected_opec_mode == MODE_MAXIMUM:
                st.warning(
                    "Exige casos completos de dificultad editorial 8–10 y desactiva ayudas. "
                    "No es una dificultad oficial de la CNSC."
                )
            if st.button(
                "▶️ Preparar esta práctica",
                type="primary",
                use_container_width=True,
                key="start_selected_opec_practice",
            ):
                st.session_state["opec_run"] = True
                st.session_state["opec_n"] = num_q_opec
                st.session_state["opec_practice_mode"] = selected_opec_mode
                st.session_state["opec_mode_topics"] = selected_mode_topics
                st.session_state["opec_mode_competencies"] = selected_mode_competencies
                st.session_state["opec_function_filter"] = selected_mode_functions
                st.rerun()
            with st.expander("Administración del banco", expanded=False):
                if AuthManager.is_admin():
                    if st.button("🤖 Crear candidatos para la OPEC", use_container_width=True):
                        st.switch_page("pages/4_Generador_IA.py")
                else:
                    st.caption(
                        "El administrador puede cubrir las brechas detectadas sin "
                        "interrumpir tu plan diario."
                    )
        else:
            st.warning("No has configurado una OPEC todavía.")
            if st.button("Configurar mi OPEC ahora"):
                st.switch_page("pages/15_Centro_OPEC.py")

# LOGIC HANDLER
final_query_filters = {}
run_sim = False
requested_session_kind = "practice"
diagnostic_requested = False
use_opec_mode_builder = False
requested_practice_mode = MODE_RECOMMENDED

if submitted_profile:
    run_sim = True
    st.session_state.pop("practice_format_notice", None)
    # Logic for Profile Mode
    final_query_filters = {
        "topics": profile_topics, # From get_profile_topics above
        "difficulties": difficulty_profile,
        "only_situational": only_situational # From toggle above
    }
    num_questions = num_questions_profile

if submitted_manual:
    run_sim = True
    st.session_state.pop("practice_format_notice", None)
    final_query_filters = {
        "tracks": track_filter,
        "competencies": competency_filter,
        "topics": topic_filter,
        "difficulties": difficulty_filter,
        "only_situational": only_situational_manual,
        "hardcore": hardcore_mode
    }

    num_questions = num_questions_profile # This looks like a copy-paste error in original code too, should be num_questions from manual form?
    # Correcting manual num_questions to use the slider from manual tab "num_q_manual" not profile
    # Actually wait, let's check variable names.
    # Manual slider: num_questions = st.slider(..., key="num_q_manual") -> variable is num_questions
    # Profile slider: num_questions_profile = st.slider(...) -> variable is num_questions_profile
    
    # So for manual, I should use 'num_questions' variable defined in line 62.
    # But line 62 is inside a form, so it might be scoped out? No, python scope is function level.
    # However, line 204 in original code said: num_questions = num_questions_profile. That was wrong for manual mode!
    
    num_questions = st.session_state.get("num_q_manual", 20)

if st.session_state.get("opec_run"):
    run_sim = True
    use_opec_mode_builder = True
    requested_practice_mode = st.session_state.get(
        "opec_practice_mode", MODE_RECOMMENDED
    )
    db_o = get_db()
    u_id = st.session_state.get("user_id")
    opec = db_o.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
    db_o.close()
    
    # Heuristic: search in stem or topic for words in functions
    # (Simple version: just use all for now but prioritize adaptive)
    final_query_filters = {
        "only_situational": True,
        "topics": st.session_state.get("opec_mode_topics", []),
        "competencies": st.session_state.get("opec_mode_competencies", []),
        "hardcore": requested_practice_mode == MODE_MAXIMUM,
    }
    num_questions = st.session_state.get("opec_n", 15)
    selected_manual_functions = st.session_state.get("opec_function_filter", [])
    requested_session_kind = f"training_{requested_practice_mode}"
    st.session_state["opec_run"] = False

if st.session_state.get("diagnostic_run"):
    run_sim = True
    diagnostic_requested = True
    requested_session_kind = "diagnostic"
    db_o = get_db()
    u_id = st.session_state.get("user_id")
    opec = db_o.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
    db_o.close()
    final_query_filters = {"only_situational": True, "hardcore": True}
    num_questions = 9
    st.session_state["diagnostic_run"] = False

if run_sim:
    db = None
    try:
        db = get_db()
        
        # 1. Fetch Candidates (High Precision OPEC Filtering v48.1)
        user_id = st.session_state.get("user_id")
        opec = db.query(UserOPEC).filter_by(
            user_id=user_id, is_active=True
        ).first()
        
        # Si venimos de la pestaña OPEC, forzamos el filtrado por OPEC
        # Si venimos de manual, el servicio igual aplica los filtros base de la meta activa del usuario
        all_candidates = QuestionService.get_questions_for_user(db, user_id)
        
        # Apply UI Filters (In-Memory Python Filtering)
        final_candidates = []
        for q in all_candidates:
            # Track Filter
            if final_query_filters.get("tracks") and q.track not in final_query_filters["tracks"]:
                continue
            # Competency Filter
            if final_query_filters.get("competencies") and q.competency not in final_query_filters["competencies"]:
                continue
            # Topic Filter
            if final_query_filters.get("topics") and q.topic not in final_query_filters["topics"]:
                continue
            # Difficulty Filter
            if (
                final_query_filters.get("difficulties")
                and editorial_question_difficulty(q) not in final_query_filters["difficulties"]
            ):
                continue
            # Strict Situational Filter (From Toggle)
            if final_query_filters.get("only_situational", False):
                if str(getattr(q, "question_type", "SITUATIONAL")).upper() != "SITUATIONAL":
                    continue
            
            final_candidates.append(q)
            
        selected_candidates = final_candidates
        if "selected_manual_functions" in locals():
            situational_case_candidates = [
                question for question in selected_candidates
                if question_format_status(question) == OFFICIAL_LABEL
                and matches_manual_function_filter(
                    question, opec.opec_number, selected_manual_functions
                )
            ]
            if len(situational_case_candidates) >= 3:
                selected_candidates = situational_case_candidates
                st.session_state["practice_format_notice"] = "SITUATIONAL_CASES"
            else:
                st.session_state["practice_format_notice"] = "SITUATIONAL_FALLBACK"
        
        # 2. Build either a valid nine-function diagnostic or the adaptive mix.
        u_id = st.session_state.get("user_id")
        competition_id = get_active_competition_id(db, u_id)
        if diagnostic_requested:
            if opec is None:
                raise ValueError("Primero selecciona una OPEC activa.")
            if not inspect(db.connection()).has_table("question_revisions"):
                raise ValueError("Falta aplicar la migración de evidencia Fase 2.")
            prior_events = []
            if (
                opec is not None
                and inspect(db.connection()).has_table("opec_learning_events")
            ):
                prior_events = (
                    db.query(OpecLearningEvent)
                    .join(OpecLearningSession)
                    .filter(
                        OpecLearningSession.user_id == u_id,
                        OpecLearningSession.competition_id == competition_id,
                        OpecLearningSession.user_opec_id == opec.id,
                    )
                    .all()
                )
            diagnostic_candidates = []
            question_by_revision = {}
            for question in selected_candidates:
                function_number = function_number_for_question(
                    question, opec.opec_number
                )
                if function_number not in range(1, 10) or not question.case_id:
                    continue
                revision = ensure_question_revision(
                    db, question, bank_partition="training"
                )
                candidate = DiagnosticCandidate(
                    question_id=str(question.question_id),
                    case_id=str(question.case_id),
                    function_number=function_number,
                    revision_id=str(revision.id),
                    trusted=True,
                    bank_partition="training",
                    question_type=str(question.question_type or "SITUATIONAL"),
                    track=str(question.track or "FUNCIONAL"),
                )
                diagnostic_candidates.append(candidate)
                question_by_revision[candidate.revision_id] = question
            diagnostic_result = select_diagnostic(
                diagnostic_candidates,
                DiagnosticPolicy(
                    allowed_partitions=("training",),
                    partition_preference=("training",),
                ),
                excluded_question_ids={event.question_id for event in prior_events},
                excluded_case_ids={event.case_id for event in prior_events if event.case_id},
                excluded_revision_ids={event.question_revision_id for event in prior_events},
            )
            if not diagnostic_result.diagnostic_valid:
                st.session_state["diagnostic_gaps"] = [
                    {
                        "function_number": gap.function_number,
                        "missing": gap.missing,
                    }
                    for gap in diagnostic_result.gaps
                ]
                db.rollback()
                st.error(
                    "No hay cobertura confiable y nueva para las nueve funciones. "
                    "No se creó un diagnóstico parcial."
                )
                selected = []
            else:
                selected = [
                    question_by_revision[item.revision_id]
                    for item in diagnostic_result.selection
                ]
                st.session_state.pop("diagnostic_gaps", None)
                db.commit()
        else:
            skills = db.query(Skill).filter_by(
                user_id=u_id, competition_id=competition_id
            ).all()
            skills_map = {(s.track, s.competency, s.topic): s for s in skills}
            prior_events = []
            if inspect(db.connection()).has_table("opec_learning_events"):
                prior_events = (
                    db.query(OpecLearningEvent)
                    .join(
                        OpecLearningSession,
                        OpecLearningEvent.session_id == OpecLearningSession.id,
                    )
                    .filter(
                        OpecLearningEvent.user_id == u_id,
                        OpecLearningSession.competition_id == competition_id,
                        OpecLearningSession.user_opec_id == opec.id,
                    )
                    .all()
                )
            exposure_counts = Counter(
                str(event.question_id) for event in prior_events
            )
            if use_opec_mode_builder and requested_practice_mode == MODE_RECOMMENDED:
                exposure_limited = [
                    question
                    for question in selected_candidates
                    if exposure_counts[str(question.question_id)] < 3
                ]
                selected = select_questions_for_simulation(
                    exposure_limited, skills_map, n=num_questions
                )
            elif use_opec_mode_builder:
                error_question_ids = set()
                error_topic_ids = set()
                if (
                    requested_practice_mode == MODE_ERRORS
                    and inspect(db.connection()).has_table("error_episodes")
                ):
                    episodes = (
                        db.query(ErrorEpisode)
                        .filter_by(
                            user_id=u_id,
                            competition_id=competition_id,
                            user_opec_id=opec.id,
                        )
                        .filter(
                            ErrorEpisode.status.notin_(("overcome", "dismissed"))
                        )
                        .all()
                    )
                    event_by_id = {str(event.id): event for event in prior_events}
                    for episode in episodes:
                        error_question_ids.add(str(episode.question_id))
                        event = event_by_id.get(str(episode.learning_event_id))
                        if event is None:
                            continue
                        if event.topic_label:
                            error_topic_ids.add(str(event.topic_label))
                        if event.function_number:
                            error_topic_ids.add(f"F{event.function_number}")
                mode_result = select_practice_questions(
                    selected_candidates,
                    mode=requested_practice_mode,
                    requested_count=num_questions,
                    opec_number=opec.opec_number,
                    exposure_counts=exposure_counts,
                    max_exposures=3,
                    topics=st.session_state.get("opec_mode_topics", []),
                    competencies=st.session_state.get(
                        "opec_mode_competencies", []
                    ),
                    function_numbers=selected_manual_functions,
                    error_question_ids=error_question_ids,
                    error_topic_ids=error_topic_ids,
                )
                if (
                    requested_practice_mode in STRICT_COMPLETENESS_MODES
                    and not mode_result.complete
                ):
                    st.error(mode_result.reason)
                    selected = []
                else:
                    selected = list(mode_result.questions)
                    if not mode_result.complete:
                        st.warning(mode_result.reason)
            else:
                selected = select_questions_for_simulation(
                    selected_candidates, skills_map, n=num_questions
                )
        
        if not selected:
            st.error("No hay preguntas disponibles con estos criterios.")
        else:
            # Initialize Exam Session State
            st.session_state["exam_mode"] = True
            st.session_state["exam_questions"] = [q.question_id for q in selected] # Store IDs
            st.session_state["current_idx"] = 0
            st.session_state["answers"] = {} # {q_id: chosen_key}
            st.session_state["checked_answers"] = {}
            st.session_state["confidences"] = {}
            st.session_state["error_types"] = {}
            st.session_state["error_reasoning"] = {}
            st.session_state["question_times"] = {}
            st.session_state["practice_aids_used"] = False
            st.session_state["hardcore_mode"] = final_query_filters.get("hardcore", False)
            st.session_state["study_session_kind"] = requested_session_kind
            st.session_state["practice_mode"] = (
                requested_practice_mode if use_opec_mode_builder else "custom"
            )
            st.session_state["exam_scope"] = {
                "competition_id": competition_id,
                "opec_number": str(opec.opec_number),
            }
            st.session_state["exam_start_time"] = time.time()
            st.session_state["total_time_limit"] = max(10 * 60, len(selected) * 120)
            
            st.switch_page("pages/2_Ejecucion.py")
    except Exception as e:
        log_ui_exception("practice.prepare", e)
        st.error("⚠️ No fue posible preparar el simulacro.")
        st.info("La preparación no pudo completarse. Recarga una vez; si continúa, revisa el banco y el alcance de la OPEC activa.")
    finally:
        if db is not None:
            db.close()

# If logic for exam is running (legacy check, but kept for safety)
if st.session_state.get("exam_mode"):
    st.switch_page("pages/2_Ejecucion.py")
