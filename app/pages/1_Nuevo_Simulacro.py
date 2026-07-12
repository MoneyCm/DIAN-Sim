import streamlit as st
import os, sys

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
import pandas as pd

from db.session import SessionLocal
from db.models import Question, Skill, UserOPEC
from core.adaptive import select_questions_for_simulation
from ui_utils import load_css, render_header, render_custom_sidebar
# V51.1: Nuclear Option - Direct Definition
import core.profiles
import importlib
try:
    importlib.reload(core.profiles)
    from core.profiles import PROFILES, get_profile_topics
except:
    pass

# FALLBACK DEFINITION (To Bypass Streamlit Caching Issues)
# SI lees esto, es porque el reload falló.
PROFILES = {
    "Gestor II (Código 302, Grado 02)": core.profiles.PROFILES.get("Gestor II (Código 302, Grado 02)"),
    "Gestor III (OPEC 236769)": {
        "description": "Perfil Profesional especializado en Fiscalización, Investigación Tributaria, Detección de Evasión, Elusión, Contrabando, Lavado de Activos y Control Cambiario (Grado 3, Código 303).",
        "salary": 9346562,
        "salary_validity": "2025",
        "vacancies": 21,
        "selection_process": "DIAN 2676 - Ingreso",
        "registration_closing": "2026-02-07",
        "functional_tracks": {
            "FUNCIONAL": [
                "Fiscalización",
                "Procedimiento Tributario",
                "Investigación Tributaria",
                "Detección de Evasión y Elusión",
                "Lavado de Activos",
                "Régimen Sancionatorio", 
                "Práctica de Pruebas",
                "Actos Administrativos",
                "Fiscalización Aduanera y Cambiaria",
                "Análisis de Denuncias y Precrítica"
            ],
            "INTEGRIDAD": [
                "Ética Pública",
                "Código Disciplinario",
                "Transparencia"
            ]
        },
        "behavioral_competencies": [
            "Análisis de Información", 
            "Pensamiento Crítico",
            "Toma de Decisiones",
            "Trabajo en Equipo",
            "Comunicación Efectiva",
            "Orientación al Logro"
        ],
        "raw_text": """
        Nivel: Profesional  Denominación: GESTOR III  Grado: 3  Código: 303  Número OPEC: 236769
        Asignación Salarial: $9,346,562  Vigencia Salarial: 2025
        Proceso de Selección: DIAN 2676 - Ingreso  Cierre de Inscripciones: 2026-02-07
        Total de Vacantes: 21

        Propósito:
        AT-FL-3006. DESARROLLAR, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, INVESTIGACIONES PARA LA VERIFICACION DEL CUMPLIMIENTO DE OBLIGACIONES EN MATERIA TRIBUTARIA, ADUANERA O CAMBIARIA, ASI ASÍ COMO LA DETECCION DE PRACTICAS TENDIENTES A LA ELUSION, EVASION, ABUSO, CONTRABANDO Y LAVADO DE ACTIVOS, DE ACUERDO CON LA NORMATIVA VIGENTE, LOS PROCEDIMIENTOS ESTABLECIDOS Y LAS DIRECTRICES INSTITUCIONALES.

        Funciones:
        1. HACER EL ANALISIS PRELIMINAR DE LAS DENUNCIAS DE FISCALIZACION RECIBIDAS, ESTABLECIENDO LA PERTINENCIA DEL INICIO DE UNA ACCION DE FISCALIZACION, DE ACUERDO CON LA NORMATIVA VIGENTE, PROCEDIMIENTOS Y LINEAMIENTOS INSTITUCIONALES.
        2. HACER LA PRECRITICA Y CLASIFICACION DE LOS INSUMOS RECIBIDOS, ESTABLECIENDO LA PERTINENCIA DEL INICIO DE UNA INVESTIGACION, DE ACUERDO CON LOS PROCEDIMIENTOS Y LINEAMIENTOS INSTITUCIONALES.
        3. LAS SEÑALADAS COMO COMUNES A TODOS LOS EMPLEOS DE LA PLANTA DE PERSONAL DE LA ENTIDAD, INCLUIDAS EN LA RESOLUCION QUE ADOPTA O MODIFICA EL MANUAL Y LAS DEMAS ASIGNADAS POR AUTORIDAD COMPETENTE, DE ACUERDO CON EL NIVEL, GRADO DE RESPONSABILIDAD Y EL AREA DE DESEMPEÑO DEL EMPLEO.
        4. ORGANIZAR LA INFORMACION Y PROPUESTAS DE ASUNTOS DE FISCALIZACION PARA PRESENTARLOS A CONSIDERACION DE LA REUNION DEL NIVEL DIRECTIVO DEL PROCESO DE FISCALIZACION Y LIQUIDACION PARA LA DECISION PERTINENTE.
        5. PARTICIPAR EN LA EJECUCION DE ACCIONES DE FISCALIZACION, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, TENDIENTES A LA VERIFICACION DEL CUMPLIMIENTO DE LAS OBLIGACIONES TRIBUTARIAS, ADUANERAS O CAMBIARIAS, DE ACUERDO CON LA NORMATIVA VIGENTE, LINEAMIENTOS INSTITUCIONALES Y PROCEDIMIENTOS ESTABLECIDOS.
        6. PROFERIR LOS ACTOS ADMINISTRATIVOS DE TRAMITE, PREPARATORIOS Y DE FONDO REQUERIDOS DENTRO DEL PROCESO, DE ACUERDO CON LA NORMATIVA VIGENTE Y LOS PROCEDIMIENTOS ESTABLECIDOS.
        7. REALIZAR INVESTIGACIONES PARA DETERMINAR EL CUMPLIMIENTO DE LAS OBLIGACIONES TRIBUTARIAS, ADUANERAS O CAMBIARIAS Y, EL REPORTE DE LAS OPERACIONES SOSPECHOSAS DE LAVADO DE ACTIVOS Y FINANCIACION DEL TERRORISMO, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, DE ACUERDO CON LA NORMATIVA VIGENTE, LAS DIRECTRICES INSTITUCIONALES Y LOS PROCEDIMIENTOS ESTABLECIDOS.
        8. REALIZAR LA PRACTICA DE PRUEBAS SOLICITADAS POR UNA DEPENDENCIA DEL NIVEL CENTRAL O SECCIONAL, PARA QUE OBRE DENTRO DE UNA INVESTIGACION, DE ACUERDO CON LA NORMATIVA VIGENTE Y LOS PROCEDIMIENTOS ESTABLECIDOS.
        9. REVISAR TECNICA Y O JURIDICAMENTE, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, LOS EXPEDIENTES Y ASUNTOS ASIGNADOS PROPIOS DEL PROCESO, DE ACUERCO CON LA NORMATIVA VIGENTE Y LAS DIRECTRICES INSTITUCIONALES.

        Requisitos:
        - Estudio: Título de PROFESIONAL en NBC: ADMINISTRACION, O NBC: CIENCIA POLITICA, RELACIONES INTERNACIONALES, O NBC: CONTADURIA PUBLICA, O NBC: DERECHO Y AFINES, O NBC: ECONOMIA, O NBC: INGENIERIA ADMINISTRATIVA Y AFINES, O NBC: INGENIERIA DE SISTEMAS, TELEMATICA Y AFINES, O NBC: INGENIERIA INDUSTRIAL Y AFINES, O NBC: INGENIERIA QUIMICA Y AFINES, O NBC: MATEMATICAS, ESTADISTICA Y AFINES.
        - Experiencia: Doce (12) meses de EXPERIENCIA PROFESIONAL RELACIONADA y Doce (12) meses de EXPERIENCIA PROFESIONAL.
        - Otros: Tarjeta Profesional en los casos señalados por la Ley.
        """
    }
}

def get_db():
    return SessionLocal()

from core.auth import AuthManager

# UI Setup
# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión en la página principal.")
    st.stop()

# UI Setup
load_css()
render_custom_sidebar()
render_header(title="Práctica por Temas", subtitle="Configura los parámetros de tu sesión de estudio")

with st.container():
    st.markdown('<div class="dian-card">', unsafe_allow_html=True)
    
    # Tabs for Mode
    tab_manual, tab_profile, tab_opec = st.tabs(["🎛️ Configuración Manual", "👤 Preparación por Cargo", "🎯 Mi Meta OPEC"])
    
    # --- MANUAL MODE ---
    with tab_manual:
        with st.form("manual_sim_form"):
            st.markdown("**Configuración de Sesión**")
            num_questions = st.slider("Cantidad de preguntas", 5, 200, 20, key="num_q_manual")
            
            st.markdown("<br>**Filtros Opcionales** (Dejar vacío para incluir todo)", unsafe_allow_html=True)
            
            # Get available options with error handling
            try:
                db_temp = get_db()
                all_tracks = [t[0] for t in db_temp.query(Question.track).distinct().all() if t[0]]
                all_competencies = [t[0] for t in db_temp.query(Question.competency).distinct().all() if t[0]]
                all_topics = [t[0] for t in db_temp.query(Question.topic).distinct().all() if t[0]]
                db_temp.close()
            except Exception as e:
                st.error(f"Error de conexión con la base de datos: {e}")
                st.info("Intenta recargar la página o verifica tu conexión a internet.")
                all_tracks, all_competencies, all_topics = [], [], []

            col1, col2 = st.columns(2)
            with col1:
                track_filter = st.multiselect("Eje (Track)", sorted(all_tracks))
                difficulty_filter = st.multiselect("Dificultad", [1, 2, 3], format_func=lambda x: {1: "🟢 Básico", 2: "🟡 Intermedio", 3: "🔴 Avanzado"}[x])
            with col2:
                competency_filter = st.multiselect("Competencia", sorted(all_competencies))
            
            topic_filter = st.multiselect("Tema Específico", sorted(all_topics))
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                only_situational_manual = st.toggle("Solo preguntas situacionales", value=True, help="Filtra para mostrar solo preguntas que plantean casos prácticos.", key="only_sit_manual")
            with col_t2:
                hardcore_mode = st.toggle("🛡️ Modo Hardcore DIAN", value=False, help="Simula el examen real: mezcla temas, oculta respuestas hasta el final y aplica tiempos estrictos.")
            
            submitted_manual = st.form_submit_button("🚀 Iniciar Simulacro Manual", type="primary")

    # --- PROFILE MODE ---
    with tab_profile:
        st.info("Selecciona el cargo al que aspiras para enfocar el estudio en sus funciones y competencias específicas.")
        
        selected_profile_name = st.selectbox("Seleccionar Cargo / Perfil", list(PROFILES.keys()))
        
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
                num_questions_profile = st.slider("Cantidad de preguntas", 5, 200, 20, key="num_q_profile")
            with col_p2:
                difficulty_profile = st.multiselect("Nivel de Dificultad", [1, 2, 3], default=[1, 2, 3], format_func=lambda x: {1: "🟢 Básico", 2: "🟡 Intermedio", 3: "🔴 Avanzado"}[x], key="diff_profile")

            # Check availability
            try:
                db_chk = get_db()
                query_chk = db_chk.query(Question).filter(Question.topic.in_(profile_topics))
                if difficulty_profile:
                    query_chk = query_chk.filter(Question.difficulty.in_(difficulty_profile))
                available_count = query_chk.count()
                db_chk.close()
                
                if available_count < 5:
                    st.warning(f"⚠️ Solo hay {available_count} preguntas disponibles para estos temas en tu banco local.")
                    st.markdown("Recomendación: Usa el **Generador IA** para crear preguntas específicas para este cargo.")
                    if st.button("Ir al Generador IA (Preguntas Situacionales)"):
                        st.session_state["ai_default_text"] = profile_data["raw_text"]
                        st.session_state["ai_default_topic"] = selected_profile_name
                        st.session_state["ai_default_diff"] = difficulty_profile[0] if len(difficulty_profile) == 1 else 2
                        st.switch_page("pages/4_Generador_IA.py")
                else:
                    st.success(f"✅ Hay {available_count} preguntas disponibles para este perfil.")
            except Exception as e:
                st.error("⚠️ Error al consultar el banco. Es posible que la base de datos se esté actualizando.")
                available_count = 0
        
        st.markdown("---")
        only_situational = st.toggle("Solo preguntas situacionales (Nuevas)", value=True, help="Filtra para mostrar solo preguntas que plantean casos prácticos generados con el nuevo sistema.")

        if st.button("🚀 Iniciar Simulacro por Perfil", type="primary", disabled=(available_count == 0)):
             submitted_profile = True
        else:
             submitted_profile = False

    # --- OPEC MODE (NEW Fase 2) ---
    with tab_opec:
        db_opec = get_db()
        u_id = st.session_state.get("user_id")
        active_opec = db_opec.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
        db_opec.close()
        
        if active_opec:
            st.success(f"🎯 **Meta Actual:** {active_opec.job_title} (OPEC {active_opec.opec_number})")
            st.markdown(f"**Propósito:** {active_opec.purpose}")
            
            with st.expander("Ver Manual de Funciones", expanded=False):
                if active_opec.functions:
                    for f in active_opec.functions:
                        st.write(f"- {f}")
            
            st.divider()
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                num_q_opec = st.number_input("Preguntas para este simulacro", 5, 100, 15, key="num_opec_q_input")
                if st.button("🚀 Iniciar Simulacro de mi OPEC", type="primary", use_container_width=True):
                    # We will filter questions that match any function keyword or topic
                    st.session_state["opec_run"] = True
                    st.session_state["opec_n"] = num_q_opec
                    st.rerun()
            
            with col_o2:
                st.info("¿No hay suficientes preguntas?")
                if st.button("🤖 Generar nuevas preguntas para mi OPEC", use_container_width=True):
                    st.switch_page("pages/4_Generador_IA.py")
        else:
            st.warning("No has configurado una OPEC todavía.")
            if st.button("Configurar mi OPEC ahora"):
                st.switch_page("pages/7_Configuracion_OPEC.py")

    st.markdown('</div>', unsafe_allow_html=True)

# LOGIC HANDLER
final_query_filters = {}
run_sim = False

if submitted_profile:
    run_sim = True
    # Logic for Profile Mode
    final_query_filters = {
        "topics": profile_topics, # From get_profile_topics above
        "difficulties": difficulty_profile,
        "only_situational": only_situational # From toggle above
    }
    num_questions = num_questions_profile

if submitted_manual:
    run_sim = True
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
    db_o = get_db()
    u_id = st.session_state.get("user_id")
    opec = db_o.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
    db_o.close()
    
    # Heuristic: search in stem or topic for words in functions
    # (Simple version: just use all for now but prioritize adaptive)
    final_query_filters = {
        "only_situational": True 
    }
    num_questions = st.session_state.get("opec_n", 15)
    st.session_state["opec_run"] = False

if run_sim:
    try:
        db = get_db()
        
        # 1. Fetch Candidates (High Precision OPEC Filtering v48.1)
        from services.question_service import QuestionService
        user_id = st.session_state.get("user_id")
        
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
            if final_query_filters.get("difficulties") and q.difficulty not in final_query_filters["difficulties"]:
                continue
            # Strict Situational Filter (From Toggle)
            if final_query_filters.get("only_situational", False):
                if "SITUACIÓN" not in q.stem.upper():
                    continue
            
            final_candidates.append(q)
            
        selected_candidates = final_candidates
        
        # 2. Fetch Skills for Adaptive Logic
        u_id = st.session_state.get("user_id")
        skills = db.query(Skill).filter_by(user_id=u_id).all()
        skills_map = {(s.track, s.competency, s.topic): s for s in skills}
        
        # 3. Select Questions
        selected = select_questions_for_simulation(selected_candidates, skills_map, n=num_questions)
        
        if not selected:
            st.error("No hay preguntas disponibles con estos criterios.")
        else:
            # Initialize Exam Session State
            st.session_state["exam_mode"] = True
            st.session_state["exam_questions"] = [q.question_id for q in selected] # Store IDs
            st.session_state["current_idx"] = 0
            st.session_state["answers"] = {} # {q_id: chosen_key}
            st.session_state["hardcore_mode"] = final_query_filters.get("hardcore", False)
            
            st.switch_page("pages/2_Ejecucion.py")
    except Exception as e:
        st.error(f"⚠️ Error al preparar el simulacro: {e}")
        st.info("Es posible que la base de datos se esté sincronizando con el nuevo Protocolo 2667. Intenta de nuevo en unos segundos.")

# If logic for exam is running (legacy check, but kept for safety)
if st.session_state.get("exam_mode"):
    st.switch_page("pages/2_Ejecucion.py")
