import streamlit as st
import os, sys

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db.session import SessionLocal
from db.models import User, Skill, Attempt, Achievement, UserStats, UserOPEC, QuestionPerformance, Question, CaseStudy, StudyPlanConfig, Competition
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload
from ui_utils import load_css, render_header
import datetime, io
from zoneinfo import ZoneInfo

from core.auth import AuthManager
from core.competitions import get_default_competition
from core.rank_system import get_rank_info
from core.anki import generate_anki_deck
from core.config import get_api_key
from core.user_keys import get_user_key
from core import adaptive as adaptive_engine

# Streamlit Cloud puede conservar el módulo anterior durante una recarga en
# caliente. El fallback evita tumbar el Dashboard mientras termina el reinicio.
build_hybrid_remaining_daily_plan = getattr(
    adaptive_engine,
    "build_hybrid_remaining_daily_plan",
    adaptive_engine.build_remaining_daily_plan,
)
count_topics_requiring_diagnosis = getattr(
    adaptive_engine,
    "count_topics_requiring_diagnosis",
    lambda questions, performances: 0,
)
from core.study_planner import build_timed_session, days_until_exam, preparation_phase
from core.motivation import build_weekly_progress, coverage_percent
from core.coverage import build_coverage_rows
from core.function_coverage import build_function_coverage
from core.opec_source_catalog import sources_for_opec_function
try:
    from core.function_coverage import build_function_study_map
except ImportError:
    # Streamlit Cloud puede conservar temporalmente el módulo anterior tras
    # desplegar una página nueva. Mantiene el Dashboard disponible hasta que
    # recargue la versión que incluye el mapa detallado.
    def build_function_study_map(functions, questions, performances, catalog_sources=None):
        rows, unmatched = build_function_coverage(functions, questions, performances)
        for row in rows:
            row["sources"] = list((catalog_sources or {}).get(row["function_number"], []))
            row["recommendation"] = (
                "El mapa detallado de fuentes estará disponible al terminar "
                "la actualización de la aplicación."
            )
        return rows, unmatched
from services.question_service import QuestionService
from core.study_resume import (
    clear_daily_run, load_daily_run, restore_daily_run_to_session, save_daily_run,
)

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión en la página principal.")
    st.stop()

load_css()
render_header(title="Panel de Control", subtitle="Analítica de progreso y gamificación")

db = SessionLocal()

try:
    # 0. OPEC Goal (NEW Fase 2)
    u_id = st.session_state.get("user_id")
    
    active_opec = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
    # Reutiliza la OPEC ya cargada para evitar repetir la consulta de usuario.
    active_competition = (
        db.get(Competition, active_opec.competition_id)
        if active_opec and active_opec.competition_id
        else get_default_competition(db)
    )
    active_competition_id = active_competition.id if active_competition else None
    competition_export_name = (
        active_competition.code.replace(" ", "_") if active_competition else "CNSC"
    )
    
    # DEBUG LINE
    # st.write(f"🔍 DEBUG DASHBOARD: User {u_id} | Active OPEC found: {active_opec}")
    
    if active_opec:
        st.markdown(f"""
        <div style="background: rgba(230, 0, 0, 0.05); border-left: 5px solid var(--dian-red); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <span style="font-size: 0.8rem; color: #666; font-weight: bold; text-transform: uppercase;">{active_competition.name if active_competition else "Concurso"} · OPEC {active_opec.opec_number}</span><br>
            <span style="font-size: 1.2rem; font-weight: 800; color: #1e293b;">{active_opec.job_title}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ No has configurado una OPEC. Ve a 'Configuración OPEC' para enfocar tu estudio.")
        st.caption(f"Debug: No active OPEC found for user_id={u_id}")

    # Plan diario adaptativo por disponibilidad y zona horaria de Colombia.
    bogota_now = datetime.datetime.now(ZoneInfo("America/Bogota"))
    study_config = db.query(StudyPlanConfig).filter_by(
        user_id=u_id,
        competition_id=active_competition_id,
    ).first()
    configured_days = study_config.study_days if study_config and study_config.study_days else [0, 1, 2, 3, 4, 5]
    is_study_day = bogota_now.weekday() in configured_days
    configured_minutes = (
        study_config.saturday_minutes
        if study_config and bogota_now.weekday() == 5
        else (study_config.daily_minutes if study_config else 30)
    )
    timed_session = build_timed_session(configured_minutes)
    daily_goal = timed_session.question_goal
    local_day_start = datetime.datetime.combine(
        bogota_now.date(), datetime.time.min, tzinfo=bogota_now.tzinfo
    )
    utc_day_start = local_day_start.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    utc_day_end = (
        local_day_start + datetime.timedelta(days=1)
    ).astimezone(datetime.timezone.utc).replace(tzinfo=None)

    today_attempt_rows = db.query(Attempt.question_id, Attempt.is_correct).join(Question).filter(
        Attempt.user_id == u_id,
        Question.competition_id == active_competition_id,
        Attempt.created_at >= utc_day_start,
        Attempt.created_at < utc_day_end,
    ).all()
    completed_today_ids = {row.question_id for row in today_attempt_rows}
    completed_today = min(len(completed_today_ids), daily_goal)
    review_now_utc = datetime.datetime.utcnow()
    due_review_count = db.query(QuestionPerformance).join(Question).filter(
        Question.competition_id == active_competition_id,
        QuestionPerformance.user_id == u_id,
        or_(
            QuestionPerformance.next_review <= review_now_utc,
            and_(
                QuestionPerformance.next_review.is_(None),
                QuestionPerformance.misses > 0,
            ),
        ),
    ).count()
    daily_accuracy = (
        sum(1 for row in today_attempt_rows if row.is_correct) / len(today_attempt_rows) * 100
        if today_attempt_rows
        else 0.0
    )

    try:
        daily_candidates = QuestionService.get_questions_for_user(
            db, u_id, competition_id=active_competition_id, user_opec=active_opec
        )
    except TypeError as exc:
        # Compatibilidad durante el reinicio de Streamlit Cloud si conserva
        # temporalmente una versión anterior de QuestionService en memoria.
        if "unexpected keyword argument" not in str(exc):
            raise
        daily_candidates = QuestionService.get_questions_for_user(db, u_id)
    daily_skills = db.query(Skill).filter_by(
        user_id=u_id, competition_id=active_competition_id
    ).all()
    daily_performances = (
        db.query(QuestionPerformance)
        .join(Question)
        .filter(
            QuestionPerformance.user_id == u_id,
            Question.competition_id == active_competition_id,
        )
        .all()
    )
    daily_skills_map = {
        (item.track, item.competency, item.topic): item for item in daily_skills
    }
    daily_performance_map = {
        item.question_id: item for item in daily_performances
    }
    daily_plan = build_hybrid_remaining_daily_plan(
        daily_candidates,
        daily_skills_map,
        daily_performance_map,
        completed_question_ids=completed_today_ids,
        daily_goal=daily_goal,
        now=bogota_now,
    )
    topics_pending_diagnosis = count_topics_requiring_diagnosis(
        daily_candidates, daily_performance_map
    )
    active_daily_run = load_daily_run(db, u_id)
    if completed_today >= daily_goal and active_daily_run:
        clear_daily_run(db, u_id)
        db.commit()
        active_daily_run = None

    if st.session_state.pop("start_daily_after_review", False):
        if active_daily_run:
            restore_daily_run_to_session(st.session_state, active_daily_run)
            st.switch_page("pages/2_Ejecucion.py")
        elif daily_plan:
            active_daily_run = save_daily_run(db, u_id, {
                "question_ids": [item.question.question_id for item in daily_plan],
                "answers": {}, "checked_answers": {}, "confidences": {},
                "error_types": {}, "current_idx": 0,
                "total_time_limit": timed_session.total_minutes * 60,
                "started_at": datetime.datetime.now().timestamp(),
                "learning_complete": False,
                "learning_minutes": timed_session.learning_minutes,
            })
            restore_daily_run_to_session(st.session_state, active_daily_run)
            st.switch_page("pages/2_Ejecucion.py")

    exam_days = days_until_exam(study_config.exam_date if study_config else None, bogota_now.date())

    week_start_date = bogota_now.date() - datetime.timedelta(days=bogota_now.weekday())
    week_start_local = datetime.datetime.combine(
        week_start_date, datetime.time.min, tzinfo=bogota_now.tzinfo
    )
    week_start_utc = week_start_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    weekly_attempt_times = db.query(Attempt.created_at).join(Question).filter(
        Attempt.user_id == u_id,
        Question.competition_id == active_competition_id,
        Attempt.created_at >= week_start_utc,
    ).all()
    studied_week_days = set()
    for row in weekly_attempt_times:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=datetime.timezone.utc)
        studied_week_days.add(created_at.astimezone(bogota_now.tzinfo).date())
    weekly_progress = build_weekly_progress(
        len(studied_week_days), len(configured_days)
    )

    candidate_topic_keys = {
        (question.track, question.competency, question.topic)
        for question in daily_candidates
    }
    candidate_by_id = {
        question.question_id: question for question in daily_candidates
    }
    topic_attempts = {key: 0 for key in candidate_topic_keys}
    for performance in daily_performances:
        question = candidate_by_id.get(performance.question_id)
        if not question:
            continue
        key = (question.track, question.competency, question.topic)
        topic_attempts[key] = topic_attempts.get(key, 0) + int(performance.hits or 0) + int(performance.misses or 0)
    studied_topic_count = sum(1 for attempts in topic_attempts.values() if attempts > 0)
    topic_coverage = coverage_percent(len(candidate_topic_keys), studied_topic_count)

    with st.container(border=True):
        st.subheader("🚀 Misión de esta semana")
        mission_cols = st.columns(4)
        mission_cols[0].metric(
            "Sesiones", f"{weekly_progress.completed_days}/{weekly_progress.target_days}"
        )
        mission_cols[1].metric(
            "Temas practicados",
            f"{studied_topic_count}/{len(candidate_topic_keys)}",
            f"{topic_coverage:.0f}% de cobertura",
        )
        mission_cols[2].metric("Meta de hoy", f"{daily_goal} preguntas")
        mission_cols[3].metric("Días al examen", exam_days if exam_days is not None else "—")
        st.progress(weekly_progress.ratio)
        if weekly_progress.is_complete:
            st.success("Objetivo semanal cumplido. La constancia ya está hecha; lo adicional es opcional.")
        else:
            st.caption(
                f"Te faltan {weekly_progress.remaining_days} sesión(es) para cumplir la semana. "
                "Puedes descansar un día sin perder tu avance."
            )

    with st.container(border=True):
        st.subheader("🎯 Tu sesión guiada de hoy")
        progress_col, accuracy_col, time_col, action_col = st.columns([1, 1, 1, 1.35])
        progress_col.metric("Avance diario", f"{completed_today}/{daily_goal}")
        accuracy_col.metric(
            "Precisión de hoy",
            f"{daily_accuracy:.0f}%" if today_attempt_rows else "Sin intentos",
        )
        st.progress(completed_today / daily_goal)
        st.caption(
            f"{timed_session.review_minutes} min repaso · "
            f"{timed_session.learning_minutes} min aprendizaje · "
            f"{timed_session.practice_minutes} min práctica · "
            f"{timed_session.closing_minutes} min cierre"
        )
        if exam_days is not None:
            st.caption(f"Examen en {exam_days} días · Etapa: {preparation_phase(exam_days)}")
        else:
            st.caption("Configura la fecha estimada del examen para organizar las etapas del plan.")
        if not is_study_day:
            st.info("Hoy está configurado como descanso. Puedes estudiar si lo deseas o retomar el próximo día disponible.")
        time_col.metric("Tiempo", f"{timed_session.total_minutes} min")
        action_col.metric("Repasos vencidos", due_review_count)

        if completed_today >= daily_goal:
            st.success("Meta diaria completada. Ahora conviene descansar o hacer un repaso ligero.")
        elif daily_plan:
            plan_topics = []
            for item in daily_plan:
                if item.question.topic not in plan_topics:
                    plan_topics.append(item.question.topic)
            st.write(
                f"Te faltan {daily_goal - completed_today} preguntas. "
                f"Prioridad: {', '.join(plan_topics[:4])}."
            )
            reason_counts = {}
            for item in daily_plan:
                for reason in item.reasons:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
            reason_summary = ", ".join(
                f"{reason}: {count}"
                for reason, count in sorted(
                    reason_counts.items(), key=lambda pair: (-pair[1], pair[0])
                )[:3]
            )
            st.caption(f"Criterios principales: {reason_summary}")
            diagnostic_questions = sum(
                "diagnóstico de cobertura" in item.reasons for item in daily_plan
            )
            if topics_pending_diagnosis:
                st.info(
                    "Modo diagnóstico activo: aún faltan "
                    f"{topics_pending_diagnosis} tema(s) por medir. Esta sesión incluye "
                    f"{diagnostic_questions} pregunta(s) para ampliar cobertura antes de "
                    "concentrarse solo en las debilidades."
                )
        else:
            st.info("No hay suficientes preguntas nuevas para completar la meta de hoy.")

        st.page_link("pages/11_Plan_Estudio.py", label="Configurar tiempo y fecha", icon="🗓️")

        if due_review_count and st.button(
            "Ir a repasos de hoy", use_container_width=True, key="dashboard_due_reviews"
        ):
            st.switch_page("pages/10_Repaso_Especial.py")
        with action_col:
            if completed_today >= daily_goal:
                st.success("✅ Sesión cumplida")
                st.caption("Lo adicional de hoy es opcional.")
            else:
                action_label = (
                    "Reanudar sesión interrumpida" if active_daily_run
                    else "Continuar plan diario" if completed_today
                    else "Iniciar plan diario"
                )
                if st.button(
                    action_label,
                    type="primary",
                    use_container_width=True,
                    disabled=not daily_plan and not active_daily_run,
                ):
                    if active_daily_run:
                        restore_daily_run_to_session(st.session_state, active_daily_run)
                    elif due_review_count:
                        st.session_state["continue_daily_after_review"] = True
                        st.switch_page("pages/10_Repaso_Especial.py")
                    else:
                        active_daily_run = save_daily_run(db, u_id, {
                            "question_ids": [item.question.question_id for item in daily_plan],
                            "answers": {}, "checked_answers": {}, "confidences": {},
                            "error_types": {}, "current_idx": 0,
                            "total_time_limit": timed_session.total_minutes * 60,
                            "started_at": datetime.datetime.now().timestamp(),
                            "learning_complete": False,
                            "learning_minutes": timed_session.learning_minutes,
                        })
                        restore_daily_run_to_session(st.session_state, active_daily_run)
                    st.switch_page("pages/2_Ejecucion.py")
    if completed_today >= daily_goal:
        celebration_key = f"daily_completion_{bogota_now.date().isoformat()}"
        if not st.session_state.get(celebration_key):
            st.session_state[celebration_key] = True
            st.balloons()
            st.toast("Sesión terminada. Hoy cumpliste lo importante.", icon="✅")

    show_analytics = st.toggle(
        "Cargar métricas y paneles avanzados",
        value=False,
        key="dashboard_show_analytics",
        help="Al activarlo se habilitan análisis detallados, gráficas y herramientas de exportación.",
    )
    if not show_analytics:
        st.info("Dashboard en modo rápido. Activa **Cargar métricas y paneles avanzados** para mostrar el resto de secciones.")
        st.stop()

    with st.expander("🗺️ Control de cobertura de la OPEC", expanded=False):
        st.caption(
            "Separa disponibilidad del banco, revisión de calidad y evidencia personal. "
            "No equivale a una certificación oficial de cobertura de la ficha."
        )
        opec_functions = active_opec.functions if active_opec and isinstance(active_opec.functions, list) else []
        ficha_cols = st.columns(3)
        ficha_cols[0].metric("Propósito cargado", "Sí" if active_opec and active_opec.purpose else "No")
        ficha_cols[1].metric("Funciones cargadas", len(opec_functions))
        ficha_cols[2].metric("Preguntas aptas", len(daily_candidates))
        if not active_opec or not active_opec.purpose or not opec_functions:
            st.warning(
                "La ficha de la OPEC está incompleta. Agrega propósito y funciones en "
                "Configuración OPEC antes de interpretar la cobertura."
            )

        coverage_rows = build_coverage_rows(daily_candidates, daily_performances)
        if coverage_rows:
            coverage_df = pd.DataFrame([{
                "Macrodominio": row["area"],
                "Preguntas aptas": row["questions"],
                "Revisión reforzada": row["trusted"],
                "Temas": row["topics"],
                "Temas evaluados": row["evaluated_topics"],
                "Estado": row["status"],
            } for row in coverage_rows])
            st.dataframe(coverage_df, hide_index=True, width="stretch")
            bank_gaps = [row for row in coverage_rows if row["status"] in {"Faltan preguntas", "Revisar calidad"}]
            practice_gaps = [row for row in coverage_rows if row["status"] in {"Pendiente de práctica", "Cobertura parcial"}]
            if bank_gaps:
                st.warning("Brecha del banco: " + ", ".join(row["area"] for row in bank_gaps))
            if practice_gaps:
                st.info("Brecha de práctica: " + ", ".join(row["area"] for row in practice_gaps))
            action_cols = st.columns(3)
            with action_cols[0]:
                st.page_link("pages/7_Configuracion_OPEC.py", label="Revisar ficha OPEC", icon="📋", width="stretch")
            with action_cols[1]:
                st.page_link("pages/1_Nuevo_Simulacro.py", label="Practicar cobertura", icon="▶️", width="stretch")
            with action_cols[2]:
                if AuthManager.is_admin():
                    st.page_link("pages/4_Generador_IA.py", label="Cubrir brecha del banco", icon="🤖", width="stretch")
                else:
                    st.caption("Las brechas del banco se remiten al administrador para crear y revisar material.")
            st.caption(
                "Criterios: al menos 5 preguntas aptas por macrodominio y 3 respuestas por tema. "
                "La revisión reforzada exige verificación y fuente registrada."
            )

            if opec_functions:
                st.markdown("#### Matriz de cobertura por función")
                st.caption(
                    "Vinculación automática conservadora basada en coincidencias temáticas. "
                    "Debe revisarse cuando la CNSC publique o actualice la guía oficial."
                )
                function_rows, unmatched_questions = build_function_coverage(
                    opec_functions, daily_candidates, daily_performances
                )
                function_df = pd.DataFrame([{
                    "Función": row["label"],
                    "Preguntas vinculadas": row["questions"],
                    "Con revisión reforzada": row["trusted"],
                    "Practicadas con evidencia": row["practiced"],
                    "Estado": row["status"],
                } for row in function_rows])
                st.dataframe(function_df, hide_index=True, width="stretch")
                uncovered_functions = [
                    row for row in function_rows if row["status"] == "Faltan preguntas"
                ]
                if uncovered_functions:
                    st.error(
                        f"{len(uncovered_functions)} de {len(function_rows)} función(es) no tienen "
                        "las 5 preguntas vinculadas requeridas."
                    )
                if unmatched_questions:
                    st.caption(
                        f"{unmatched_questions} pregunta(s) aptas quedaron sin asociar por falta de "
                        "coincidencia suficiente; no se usaron para inflar la cobertura."
                    )

                st.markdown("#### Mapa de estudio por función")
                st.caption(
                    "Muestra solo fuentes vinculadas a preguntas verificadas. Si una función no tiene "
                    "fuente, no se inventa una recomendación normativa."
                )
                catalogue = {
                    index: sources_for_opec_function(active_opec.opec_number, function)
                    for index, function in enumerate(opec_functions, start=1)
                }
                study_map_rows, _ = build_function_study_map(
                    opec_functions, daily_candidates, daily_performances, catalogue
                )
                for row in study_map_rows:
                    source_text = "\n\n".join(f"- {source}" for source in row["sources"])
                    with st.expander(
                        f"{row['label']} · {row['status']}",
                        expanded=row["status"] != "Con evidencia",
                    ):
                        st.write(row["recommendation"])
                        st.caption(
                            f"Banco: {row['questions']} preguntas · "
                            f"verificadas: {row['trusted']} · "
                            f"practicadas con evidencia: {row['practiced']}"
                        )
                        if source_text:
                            st.markdown("**Fuentes verificadas para estudiar:**\n" + source_text)
                        else:
                            st.warning(
                                "Aún no hay una fuente verificada vinculada a esta función. "
                                "No generes preguntas nuevas hasta cargar la norma o procedimiento oficial."
                            )
        else:
            st.info("No hay preguntas aptas clasificadas para construir el control de cobertura.")

    # 1. User Stats & Mastery
    stats = db.query(UserStats).filter_by(user_id=u_id).first()
    if not stats:
        stats = UserStats(user_id=u_id, current_streak=0, max_streak=0, total_points=0)

    # Mastery Calculation Mikey (Resilient v22)
    mastered_qs = 0
    total_qs = 0
    try:
        performance_query = db.query(QuestionPerformance).join(Question).filter(
            QuestionPerformance.user_id == u_id,
            Question.competition_id == active_competition_id,
        )
        total_qs = performance_query.count()
        if hasattr(QuestionPerformance, "is_mastered"):
            mastered_qs = performance_query.filter(QuestionPerformance.is_mastered.is_(True)).count()
        else:
            # Fallback: estimate mastery if field is missing Mikey
            mastered_qs = 0 
    except Exception as e:
        print(f"⚠️ Error en Mastery Calculation: {e}")

    mastery_pct = (mastered_qs / total_qs * 100) if total_qs > 0 else 0

    # Quality Metrics v32 Mikey
    bank_query = db.query(Question).filter(Question.competition_id == active_competition_id)
    total_bank = bank_query.count()
    verified_bank = bank_query.filter(Question.is_verified.is_(True)).count()
    quality_idx = (verified_bank / total_bank * 100) if total_bank > 0 else 0

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("🔥 Racha Actual", f"{stats.current_streak} días")
    with col_s2:
        st.metric("🎓 Maestría Real", f"{mastery_pct:.1f}%", f"{mastered_qs}/{total_qs} Qs")
    with col_s3:
        st.metric("🏆 Puntos Totales", f"{stats.total_points} pts")
    with col_s4:
        fav_count = db.query(QuestionPerformance).join(Question).filter(
            QuestionPerformance.user_id == u_id,
            QuestionPerformance.is_favorite.is_(True),
            Question.competition_id == active_competition_id,
        ).count()
        st.metric("⭐ Favoritas", f"{fav_count} Qs", "Para repasar")

    # Quality Indicator Mikey
    st.markdown(f"""
    <div style="background: rgba(44, 62, 80, 0.05); border-radius: 10px; padding: 10px; margin-top: 10px; border-left: 5px solid #4CAF50;">
        <span style="font-size: 0.8rem; font-weight: 700;">ÍNDICE DE CALIDAD DEL BANCO: {quality_idx:.0f}%</span>
        <div style="background: #e0e0e0; height: 6px; border-radius: 3px; margin-top: 5px;">
            <div style="background: #4CAF50; width: {quality_idx}%; height: 100%; border-radius: 3px;"></div>
        </div>
        <small style="color: #666;">{verified_bank} de {total_bank} preguntas con revisión de calidad registrada.</small>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 2. Balance Global y Progreso por Eje
    col_b1, col_b2 = st.columns([1, 2])

    with col_b1:
        st.markdown('<div class="dian-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("📊 Balance Global")
        performance_scope = db.query(QuestionPerformance).join(Question).filter(
            QuestionPerformance.user_id == u_id,
            Question.competition_id == active_competition_id,
        )
        total_hits = performance_scope.with_entities(func.sum(QuestionPerformance.hits)).scalar() or 0
        total_misses = performance_scope.with_entities(func.sum(QuestionPerformance.misses)).scalar() or 0
        
        if total_hits + total_misses > 0:
            global_accuracy = total_hits / (total_hits + total_misses) * 100
            fig_balance = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=global_accuracy,
                number={"suffix": "%", "font": {"size": 36}},
                delta={"reference": 70, "suffix": " pp", "increasing": {"color": "#059669"}},
                title={"text": "Precisión acumulada", "font": {"size": 15}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar": {"color": "#1f4e79", "thickness": 0.28},
                    "steps": [
                        {"range": [0, 50], "color": "#fee2e2"},
                        {"range": [50, 70], "color": "#fef3c7"},
                        {"range": [70, 100], "color": "#d1fae5"},
                    ],
                    "threshold": {"line": {"color": "#dc2626", "width": 4}, "value": 70},
                },
            ))
            fig_balance.update_layout(
                height=270, margin=dict(t=45, b=10, l=25, r=25),
                paper_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_balance, width="stretch", key="dashboard_balance_gauge")
            st.caption(f"✅ {total_hits} aciertos · ❌ {total_misses} errores · Meta: 70%")
        else:
            st.info("No hay datos de intentos.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b2:
        st.markdown('<div class="dian-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("🎯 Nivel de Dominio por Eje")
        skills = daily_skills
        if skills:
            df_skills = pd.DataFrame([{
                'Eje': s.track,
                'Macro-Dominio': getattr(s, 'macro_dominio', "Transversal") or "Transversal",
                'Micro-Competencia': getattr(s, 'micro_competencia', s.topic) or s.topic,
                'Dominio': s.mastery_score
            } for s in skills])
            
            eje_mastery = (
                df_skills.groupby('Eje', as_index=False)['Dominio'].mean()
                .sort_values('Dominio', ascending=True)
            )
            bar_colors = [
                '#dc2626' if value < 50 else '#f59e0b' if value < 70 else '#10b981'
                for value in eje_mastery['Dominio']
            ]
            fig = go.Figure(go.Bar(
                x=eje_mastery['Dominio'], y=eje_mastery['Eje'], orientation='h',
                marker_color=bar_colors,
                text=[f"{value:.0f}%" for value in eje_mastery['Dominio']],
                textposition='outside', cliponaxis=False,
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            ))
            fig.add_vline(x=70, line_dash="dash", line_color="#991b1b",
                          annotation_text="Meta 70%", annotation_position="top")
            fig.update_xaxes(range=[0, 105], title=None, ticksuffix="%", fixedrange=True)
            fig.update_yaxes(title=None, fixedrange=True)
            fig.update_layout(
                height=max(250, 75 * len(eje_mastery)), showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=35, b=25, l=10, r=35),
            )
            st.plotly_chart(fig, width="stretch", key="dashboard_axis_mastery")
            weakest_skill = min(skills, key=lambda item: item.mastery_score or 0)
            st.warning(
                f"Prioridad actual: **{weakest_skill.topic}** "
                f"({(weakest_skill.mastery_score or 0):.0f}% de dominio)."
            )
        else:
            st.info("¡Realiza tu primer simulacro!")
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. Rendimiento en el Tiempo
    st.markdown('<div class="dian-card">', unsafe_allow_html=True)
    st.subheader("📈 Rendimiento de los últimos intentos")
    attempts = db.query(Attempt).join(Question).filter(
        Attempt.user_id == u_id,
        Question.competition_id == active_competition_id,
    ).order_by(Attempt.created_at.desc()).limit(50).all()
    if attempts:
        df_att = pd.DataFrame([{
            'Fecha': a.created_at,
            'Resultado': 1 if a.is_correct else 0
        } for a in attempts])
        
        # Agrupar por fecha
        df_att['Fecha'] = df_att['Fecha'].dt.date
        df_daily = df_att.groupby('Fecha').agg(
            Resultado=('Resultado', 'mean'), Intentos=('Resultado', 'size')
        ).reset_index()
        df_daily['Porcentaje'] = df_daily['Resultado'] * 100
        df_daily['Promedio móvil'] = df_daily['Porcentaje'].rolling(3, min_periods=1).mean()

        fig_line = go.Figure()
        fig_line.add_trace(go.Bar(
            x=df_daily['Fecha'], y=df_daily['Porcentaje'], name='Precisión diaria',
            marker_color='#bfdbfe',
            customdata=df_daily['Intentos'],
            hovertemplate="%{x}<br>Precisión: %{y:.0f}%<br>Intentos: %{customdata}<extra></extra>",
        ))
        fig_line.add_trace(go.Scatter(
            x=df_daily['Fecha'], y=df_daily['Promedio móvil'], name='Promedio móvil (3 días)',
            mode='lines+markers', line=dict(color='#1d4ed8', width=3),
        ))
        fig_line.add_hline(y=70, line_dash='dash', line_color='#dc2626',
                           annotation_text='Meta 70%', annotation_position='top left')
        fig_line.update_yaxes(range=[0, 105], ticksuffix='%', title=None, fixedrange=True)
        fig_line.update_xaxes(title=None, fixedrange=True)
        fig_line.update_layout(
            height=330, hovermode='x unified', legend=dict(orientation='h', y=1.12),
            margin=dict(t=55, b=20, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_line, width="stretch", key="dashboard_progress_chart")
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. Diagnóstico accionable de habilidades
    col_d1, col_d2 = st.columns(2)

    skill_rows = []
    for skill_item in skills:
        key = (skill_item.track, skill_item.competency, skill_item.topic)
        evidence = {"hits": 0, "misses": 0}
        for performance in daily_performances:
            candidate = candidate_by_id.get(performance.question_id)
            if candidate and (candidate.track, candidate.competency, candidate.topic) == key:
                evidence["hits"] += int(performance.hits or 0)
                evidence["misses"] += int(performance.misses or 0)
        attempts_count = evidence["hits"] + evidence["misses"]
        skill_rows.append({
            "skill": skill_item,
            "macro": getattr(skill_item, "macro_dominio", None) or "Transversal",
            "topic": skill_item.topic,
            "mastery": float(skill_item.mastery_score or 0),
            "attempts": attempts_count,
            "hits": evidence["hits"],
            "misses": evidence["misses"],
            "accuracy": (evidence["hits"] / attempts_count * 100) if attempts_count else None,
        })
    minimum_topic_attempts = 3
    evaluated_rows = [row for row in skill_rows if row["attempts"] >= minimum_topic_attempts]
    emerging_rows = [row for row in skill_rows if 0 < row["attempts"] < minimum_topic_attempts]
    pending_rows = [row for row in skill_rows if row["attempts"] == 0]

    with col_d1:
        st.subheader("🧭 Cobertura por Macro-Dominio")
        if evaluated_rows:
            evaluated_df = pd.DataFrame(evaluated_rows)
            macro_summary = (
                evaluated_df.groupby("macro", as_index=False)
                .agg(Aciertos=("hits", "sum"), Errores=("misses", "sum"), Intentos=("attempts", "sum"))
            )
            macro_summary["Dominio"] = (
                macro_summary["Aciertos"] / macro_summary["Intentos"] * 100
            )
            macro_summary = macro_summary.sort_values("Dominio", ascending=True)
            macro_colors = [
                '#dc2626' if value < 50 else '#f59e0b' if value < 70 else '#10b981'
                for value in macro_summary['Dominio']
            ]
            fig_macro = go.Figure(go.Bar(
                x=macro_summary['Dominio'], y=macro_summary['macro'], orientation='h',
                marker_color=macro_colors,
                text=[f"{value:.0f}%" for value in macro_summary['Dominio']],
                textposition='outside', cliponaxis=False,
                customdata=macro_summary['Intentos'],
                hovertemplate="%{y}<br>Dominio: %{x:.1f}%<br>Intentos: %{customdata}<extra></extra>",
            ))
            fig_macro.add_vline(x=70, line_dash='dash', line_color='#dc2626')
            fig_macro.update_xaxes(range=[0, 105], ticksuffix='%', title=None, fixedrange=True)
            fig_macro.update_yaxes(title=None, fixedrange=True)
            fig_macro.update_layout(
                height=max(260, 70 * len(macro_summary)), showlegend=False,
                margin=dict(t=15, b=20, l=10, r=35),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_macro, width="stretch", key="dashboard_macro_coverage")
            st.caption(
                f"Cobertura evaluada: {len(evaluated_rows)} de {len(skill_rows)} habilidades. "
                f"Se requieren al menos {minimum_topic_attempts} respuestas por tema. "
                "Las no practicadas no se califican como debilidades."
            )
        else:
            st.info(
                "Aún no hay evidencia suficiente para calcular tu dominio. Las respuestas del "
                "plan diario, las prácticas y los simulacros empezarán a construir el diagnóstico."
            )
            if emerging_rows:
                st.caption(
                    f"Ya comenzaste {len(emerging_rows)} tema(s), pero cada uno necesita al menos "
                    f"{minimum_topic_attempts} respuestas para producir una estimación estable."
                )

    with col_d2:
        demonstrated_weaknesses = [row for row in evaluated_rows if row["accuracy"] < 70]
        st.subheader(
            "🎯 Prioridades de refuerzo"
            if demonstrated_weaknesses else "📋 Pendiente de evaluación"
        )
        if demonstrated_weaknesses:
            priority_rows = sorted(
                demonstrated_weaknesses,
                key=lambda row: (row["accuracy"], -row["misses"], row["topic"]),
            )[:5]
            for index, row in enumerate(priority_rows, start=1):
                with st.container(border=True):
                    st.markdown(f"**{index}. {row['topic']}**")
                    st.progress(min(max(row['accuracy'] / 100, 0.0), 1.0))
                    st.caption(
                        f"Precisión {row['accuracy']:.0f}% · "
                        f"{row['attempts']} intentos · {row['misses']} errores"
                    )
            st.page_link(
                "pages/1_Nuevo_Simulacro.py", label="Practicar por tema", icon="▶️",
                width="stretch",
            )
        elif skill_rows:
            st.info(
                "Aún no hay debilidades demostradas. Se evaluarán progresivamente los "
                "macrodominios del concurso; estar pendiente no significa tener bajo desempeño."
            )
            pending_macros = sorted({row["macro"] for row in pending_rows + emerging_rows})
            if pending_macros:
                for macro in pending_macros:
                    st.markdown(f"- **{macro}** · pendiente de evidencia suficiente")
            else:
                st.success("Los macrodominios evaluados están actualmente sobre la meta del 70%.")
        else:
            st.info("No hay habilidades configuradas todavía.")

    # 5. Logros personales y siguiente meta
    col_v1, col_v2 = st.columns([2, 1])

    with col_v1:
        st.markdown('<div class="dian-card">', unsafe_allow_html=True)
        st.subheader("🏆 Logros Personales")

        achievements = db.query(Achievement).filter_by(user_id=u_id).all()
        if achievements:
            cols = st.columns(4)
            for i, ach in enumerate(achievements):
                with cols[i % 4]:
                    st.markdown(f"""
                    <div style="text-align: center; background: rgba(0,0,0,0.03); border-radius: 10px; padding: 10px;">
                        <div style="font-size: 2rem;">{ach.icon}</div>
                        <div style="font-size: 0.8rem; font-weight: 700;">{ach.name}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.write("Completa tu primera sesión para desbloquear el primer logro.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_v2:
        st.markdown('<div class="dian-card">', unsafe_allow_html=True)
        st.subheader("🎯 Próximo Logro")
        streak = int(stats.current_streak or 0)
        points = int(stats.total_points or 0)
        unlocked_names = {item.name for item in achievements}
        if "Constancia" not in unlocked_names:
            target_label = "Constancia"
            target_detail = "Estudia 3 días seguidos"
            target_progress = min(streak / 3, 1.0)
            target_value = f"{streak}/3 días"
        elif "Imparable" not in unlocked_names:
            target_label = "Imparable"
            target_detail = "Alcanza una racha de 7 días"
            target_progress = min(streak / 7, 1.0)
            target_value = f"{streak}/7 días"
        elif "Veterano" not in unlocked_names:
            target_label = "Veterano"
            target_detail = "Acumula 1.500 puntos"
            target_progress = min(points / 1500, 1.0)
            target_value = f"{points}/1.500 pts"
        else:
            target_label = "Perfección"
            target_detail = "Logra 10 respuestas correctas consecutivas"
            target_progress = 0.0
            target_value = "Nuevo desafío"
        st.markdown(f"**{target_label}**")
        st.caption(target_detail)
        st.progress(target_progress)
        st.caption(target_value)
        st.markdown('</div>', unsafe_allow_html=True)

    # 6. Herramientas Administrativas
    is_admin_user = AuthManager.is_admin()
    show_admin_tools = False
    if is_admin_user:
        st.divider()
        st.subheader("🛠️ Respaldo administrativo del banco")
        show_admin_tools = st.toggle(
            "Mostrar herramientas administrativas del banco",
            value=False,
            key="dashboard_show_admin_tools",
        )
    all_qs = (
        db.query(Question)
        .filter(Question.competition_id == active_competition_id)
        .all()
        if is_admin_user and show_admin_tools
        else []
    )

    if all_qs:
        export_data = []
        text_lines = []
        
        # Header for text version
        text_lines.append("track|competency|topic|stem|options_A|options_B|options_C|options_D|correct_key|rationale|difficulty")
        
        for q in all_qs:
            opts = q.options_json if q.options_json else {}
            
            # Data for Excel
            row = {
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
            }
            export_data.append(row)
            
            # Data for Text Format (Pipes)
            clean_stem = str(q.stem).replace("\n", " ").replace("|", " ")
            clean_rat = str(q.rationale).replace("\n", " ").replace("|", " ")
            text_row = f"{q.track}|{q.competency}|{q.topic}|{clean_stem}|{opts.get('A','')}|{opts.get('B','')}|{opts.get('C','')}|{opts.get('D','')}|{q.correct_key}|{clean_rat}|{q.difficulty}"
            text_lines.append(text_row)
        
        df_export = pd.DataFrame(export_data)
        text_content = "\n".join(text_lines)
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            output_xlsx = io.BytesIO()
            with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Banco_Preguntas')
            
            st.download_button(
                label="📥 Descargar Banco (Excel .xlsx)",
                data=output_xlsx.getvalue(),
                file_name=f"Banco_Preguntas_{competition_export_name}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_export_xlsx"
            )
            st.caption("Ideal para respaldo completo y edición profesional.")

        with col_exp2:
            st.download_button(
                label="📄 Descargar Banco (Texto/Pipes)",
                data=text_content,
                file_name=f"Banco_Preguntas_Texto_{datetime.datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="btn_export_pipes"
            )
            st.caption("Formato compatible con Copiar/Pegar (delimitado por |).")

    elif is_admin_user:
        st.warning("El banco está vacío. No hay datos para exportar.")

    st.divider()
    st.subheader("📦 Repaso fuera de DIAN Sim (opcional)")
    st.caption(
        "DIAN Sim ya programa tus repasos automáticamente. Usa Anki solamente si deseas "
        "estudiar sin conexión o conservar una copia externa."
    )
    show_anki_tools = st.toggle("Mostrar exportación avanzada a Anki", value=False)
    if not show_anki_tools:
        st.info("Recomendado: continúa con **Repasos de hoy** dentro de la aplicación.")
        db.close()
        st.stop()

    st.subheader("🎴 Exportar a Anki")

    # 1. Obtener preguntas falladas (Intentos incorrectos) - Obteniendo IDs primero para evitar DISTINCT sobre columnas JSON en Postgres
    failed_q_ids = db.query(Attempt.question_id).filter(
        Attempt.user_id == u_id,
        Attempt.is_correct == False
    ).distinct().all()
    failed_q_ids = [r[0] for r in failed_q_ids]
    failed_query = db.query(Question).options(joinedload(Question.case_study))
    if hasattr(Question, "anki_enrichment"):
        failed_query = failed_query.options(joinedload(Question.anki_enrichment))
    failed_qs = failed_query.filter(
        Question.competition_id == active_competition_id,
        Question.question_id.in_(failed_q_ids),
    ).all() if failed_q_ids else []
    # 2. Obtener preguntas favoritas
    fav_q_ids = db.query(QuestionPerformance.question_id).filter(
        QuestionPerformance.user_id == u_id,
        QuestionPerformance.is_favorite == True
    ).distinct().all()
    fav_q_ids = [r[0] for r in fav_q_ids]
    fav_query = db.query(Question).options(joinedload(Question.case_study))
    if hasattr(Question, "anki_enrichment"):
        fav_query = fav_query.options(joinedload(Question.anki_enrichment))
    fav_qs = fav_query.filter(
        Question.competition_id == active_competition_id,
        Question.question_id.in_(fav_q_ids),
    ).all() if fav_q_ids else []
    def to_anki_standard_csv(questions):
        rows = []
        for q in questions:
            opts = q.options_json if q.options_json else {}
            opts_str = "<br>".join([f"<b>{k})</b> {str(v).replace('\n', '<br>').replace('\r', '')}" for k, v in opts.items()])
            
            frente_parts = []
            frente_parts.append(f"<b>Tema:</b> {q.topic}")
            
            if q.case_study:
                cs_title = f" ({q.case_study.title})" if q.case_study.title else ""
                cs_text_formatted = q.case_study.text.replace("\n", "<br>").replace("\r", "")
                frente_parts.append(f"<b>Caso de Estudio{cs_title}:</b><br>{cs_text_formatted}")
                
            stem_formatted = q.stem.replace("\n", "<br>").replace("\r", "")
            frente_parts.append(f"<b>Pregunta:</b> {stem_formatted}")
            frente_parts.append(f"<b>Opciones:</b><br>{opts_str}")
            
            frente = "<br><br>".join(frente_parts)
            
            rationale_formatted = (q.rationale or 'N/A').replace("\n", "<br>").replace("\r", "")
            reverso = f"<b>Respuesta Correcta:</b> {q.correct_key}<br><br><b>Justificación:</b> {rationale_formatted}"
            if q.source_refs:
                source_refs_formatted = q.source_refs.replace("\n", "<br>").replace("\r", "")
                reverso += f"<br><br><b>Norma/Referencia:</b> {source_refs_formatted}"
                
            rows.append({"Frente": frente, "Reverso": reverso})
        
        df = pd.DataFrame(rows)
        csv_buffer = io.StringIO()
        import csv
        df.to_csv(csv_buffer, sep=";", index=False, header=True, quoting=csv.QUOTE_ALL, encoding="utf-8")
        return csv_buffer.getvalue()

    def to_anki_interactive_csv(questions):
        rows = []
        for q in questions:
            opts = q.options_json if q.options_json else {}
            
            caso_text = ""
            if q.case_study:
                cs_title = f"({q.case_study.title})\n" if q.case_study.title else ""
                caso_text = f"{cs_title}{q.case_study.text}".replace("\n", "<br>").replace("\r", "")
                
            stem_formatted = q.stem.replace("\n", "<br>").replace("\r", "")
            
            opcion_a = str(opts.get('A', '')).replace("\n", "<br>").replace("\r", "")
            opcion_b = str(opts.get('B', '')).replace("\n", "<br>").replace("\r", "")
            opcion_c = str(opts.get('C', '')).replace("\n", "<br>").replace("\r", "")
            opcion_d = str(opts.get('D', '')).replace("\n", "<br>").replace("\r", "")
            
            justificacion = (q.rationale or 'N/A').replace("\n", "<br>").replace("\r", "")
            norma = (q.source_refs or '').replace("\n", "<br>").replace("\r", "")
            
            rows.append({
                "Caso_Estudio": caso_text,
                "Tema": q.topic,
                "Pregunta": stem_formatted,
                "Opcion_A": opcion_a,
                "Opcion_B": opcion_b,
                "Opcion_C": opcion_c,
                "Opcion_D": opcion_d,
                "Respuesta_Correcta": q.correct_key,
                "Justificacion": justificacion,
                "Norma": norma
            })
            
        df = pd.DataFrame(rows)
        csv_buffer = io.StringIO()
        import csv
        df.to_csv(csv_buffer, sep=";", index=False, header=True, quoting=csv.QUOTE_ALL, encoding="utf-8")
        return csv_buffer.getvalue()

    def anki_enrichment_fields(question):
        enrichment = getattr(question, "anki_enrichment", None)
        if not enrichment or enrichment.status not in {"generated", "reviewed"}:
            return {"Regla_Clave": "", "Excepcion_Clave": "", "Distractor_Clave": ""}
        return {
            "Regla_Clave": enrichment.rule or "",
            "Excepcion_Clave": enrichment.exception or "",
            "Distractor_Clave": enrichment.distractor or "",
        }
    tab_estandar, tab_interactivo = st.tabs(["🎴 Estándar (Anverso/Reverso)", "🎮 Interactivo (Opción Múltiple)"])

    with tab_estandar:
        st.info("""
        💡 **¿Cómo importar tarjetas estándar en Anki?**
        1. Descarga el archivo `.csv` usando los botones de abajo.
        2. Abre **Anki** y selecciona **Archivo -> Importar**.
        3. Elige el archivo descargado.
        4. En las opciones de importación:
           - Configura el delimitador de campos como **Punto y coma** (`;`).
           - Marca la casilla **Permitir HTML en los campos**.
           - Mapea el primer campo al **Frente (Front)** y el segundo al **Reverso (Back)**.
        """)
        
        col_std1, col_std2 = st.columns(2)
        with col_std1:
            st.markdown("##### ❌ Preguntas Falladas")
            if failed_qs:
                failed_std_csv = to_anki_standard_csv(failed_qs)
                st.download_button(
                    label=f"📥 Descargar Fallas Estándar ({len(failed_qs)} Qs)",
                    data=failed_std_csv,
                    file_name=f"Anki_{competition_export_name}_Fallas_Std_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_export_anki_fallas_std"
                )
                st.caption("Importa este archivo estándar en Anki para un repaso rápido de tus errores.")
            else:
                st.info("No tienes fallas registradas todavía.")

        with col_std2:
            st.markdown("##### ⭐ Preguntas Favoritas")
            if fav_qs:
                fav_std_csv = to_anki_standard_csv(fav_qs)
                st.download_button(
                    label=f"📥 Descargar Favoritas Estándar ({len(fav_qs)} Qs)",
                    data=fav_std_csv,
                    file_name=f"Anki_{competition_export_name}_Favoritas_Std_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_export_anki_favs_std"
                )
                st.caption("Importa este archivo estándar para repasar las tarjetas que guardaste con estrella.")
            else:
                st.info("No has marcado ninguna pregunta como favorita.")

    with tab_interactivo:
        st.info("""
        💡 **¿Cómo usar tus tarjetas interactivas en Anki en 1 solo clic?**
        1. Descarga el archivo de mazo directo **`.apkg`** usando los botones de abajo.
        2. Abre el archivo descargado haciendo **doble clic** en tu computadora.
        3. ¡Listo! Anki creará automáticamente la baraja y el diseño con botones interactivos.
        
        *Nota: Si prefieres configurar tu propia plantilla manualmente, puedes descargar el archivo `.csv` y seguir el mapeo tradicional de 10 columnas.*
        """)

        export_questions = list({q.question_id: q for q in [*failed_qs, *fav_qs]}.values())
        enrichment_available = hasattr(Question, "anki_enrichment")
        if enrichment_available:
            from core.anki_enrichment import enrich_question, needs_enrichment
            pending_enrichments = [q for q in export_questions if needs_enrichment(q)]
        else:
            pending_enrichments = []
        if pending_enrichments:
            st.warning(f"Hay {len(pending_enrichments)} preguntas sin tarjetas pedagógicas enriquecidas.")
            provider = st.selectbox(
                "Proveedor para enriquecer tarjetas",
                ["Gemini", "OpenAI", "Groq", "Mistral"],
                index=0,
                key="anki_enrichment_provider",
            )
            if st.button("✨ Generar enriquecimientos faltantes", key="generate_missing_anki"):
                provider_key = provider.lower()
                api_key = get_user_key(u_id, provider_key) or get_api_key(provider_key)
                if not api_key:
                    st.error(f"Configura una API key de {provider} antes de generar.")
                else:
                    progress = st.progress(0)
                    generated = 0
                    errors = 0
                    for index, question in enumerate(pending_enrichments, start=1):
                        try:
                            enrich_question(db, question, provider_key, api_key)
                            generated += 1
                        except Exception:
                            errors += 1
                        progress.progress(index / len(pending_enrichments))
                    if errors:
                        st.warning(f"Generadas: {generated}. Errores: {errors}.")
                    else:
                        st.success(f"Se generaron {generated} enriquecimientos.")
                    st.rerun()
        elif enrichment_available:
            st.success("Todas las tarjetas seleccionadas tienen enriquecimiento pedagógico.")
        else:
            st.info("El enriquecimiento Anki se activará tras reiniciar la aplicación.")
        col_int1, col_int2 = st.columns(2)
        with col_int1:
            st.markdown("##### ❌ Preguntas Falladas (Mazo Directo)")
            if failed_qs:
                # Convertir modelos a dicts para genanki
                failed_dicts = []
                for q in failed_qs:
                    opts = q.options_json if q.options_json else {}
                    caso_text = ""
                    if q.case_study:
                        cs_title = f"({q.case_study.title})\n" if q.case_study.title else ""
                        caso_text = f"{cs_title}{q.case_study.text}"
                    
                    failed_dicts.append({
                        "Caso_Estudio": caso_text,
                        "Tema": q.topic,
                        "Pregunta": q.stem,
                        "Opcion_A": opts.get('A', ''),
                        "Opcion_B": opts.get('B', ''),
                        "Opcion_C": opts.get('C', ''),
                        "Opcion_D": opts.get('D', 'N/A'),
                        "Respuesta_Correcta": q.correct_key,
                        "Justificacion": q.rationale or 'N/A',
                        "Norma": q.source_refs or '',
                        **anki_enrichment_fields(q)
                    })
                
                # Generar mazo APKG
                try:
                    failed_apkg = generate_anki_deck(failed_dicts, f"{competition_export_name} - Fallas Interactivas")
                    st.download_button(
                        label="📥 Descargar Mazo APKG (Anki Directo)",
                        data=failed_apkg,
                        file_name=f"{competition_export_name}_Fallas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.apkg",
                        mime="application/apkg",
                        use_container_width=True,
                        key="btn_export_anki_fallas_apkg"
                    )
                except Exception as ex:
                    st.error(f"Error generando APKG: {ex}")
                
                failed_int_csv = to_anki_interactive_csv(failed_qs)
                st.download_button(
                    label="📥 Descargar Respuestas en CSV (Excel)",
                    data=failed_int_csv,
                    file_name=f"Anki_{competition_export_name}_Fallas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_export_anki_fallas_int"
                )
                st.caption("Usa el botón APKG para importar todo en 1 clic. Usa el CSV si prefieres abrirlo en Excel.")
            else:
                st.info("No tienes fallas registradas todavía.")

        with col_int2:
            st.markdown("##### ⭐ Preguntas Favoritas (Mazo Directo)")
            if fav_qs:
                # Convertir modelos a dicts para genanki
                fav_dicts = []
                for q in fav_qs:
                    opts = q.options_json if q.options_json else {}
                    caso_text = ""
                    if q.case_study:
                        cs_title = f"({q.case_study.title})\n" if q.case_study.title else ""
                        caso_text = f"{cs_title}{q.case_study.text}"
                    
                    fav_dicts.append({
                        "Caso_Estudio": caso_text,
                        "Tema": q.topic,
                        "Pregunta": q.stem,
                        "Opcion_A": opts.get('A', ''),
                        "Opcion_B": opts.get('B', ''),
                        "Opcion_C": opts.get('C', ''),
                        "Opcion_D": opts.get('D', 'N/A'),
                        "Respuesta_Correcta": q.correct_key,
                        "Justificacion": q.rationale or 'N/A',
                        "Norma": q.source_refs or '',
                        **anki_enrichment_fields(q)
                    })
                
                # Generar mazo APKG
                try:
                    fav_apkg = generate_anki_deck(fav_dicts, f"{competition_export_name} - Favoritas Interactivas")
                    st.download_button(
                        label="📥 Descargar Mazo APKG (Anki Directo)",
                        data=fav_apkg,
                        file_name=f"{competition_export_name}_Favoritas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.apkg",
                        mime="application/apkg",
                        use_container_width=True,
                        key="btn_export_anki_favs_apkg"
                    )
                except Exception as ex:
                    st.error(f"Error generando APKG: {ex}")
                
                fav_int_csv = to_anki_interactive_csv(fav_qs)
                st.download_button(
                    label="📥 Descargar Respuestas en CSV (Excel)",
                    data=fav_int_csv,
                    file_name=f"Anki_{competition_export_name}_Favoritas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_export_anki_favs_int"
                )
                st.caption("Usa el botón APKG para importar todo en 1 clic. Usa el CSV si prefieres abrirlo en Excel.")
            else:
                st.info("No has marcado ninguna pregunta como favorita.")

    st.divider()
    st.subheader("⚙️ Otras Acciones")
    if "confirm_delete_stats" not in st.session_state:
        st.session_state["confirm_delete_stats"] = False

    if not st.session_state["confirm_delete_stats"]:
        if st.button("🗑️ Reiniciar Estadísticas de Usuario", use_container_width=True):
            st.session_state["confirm_delete_stats"] = True
            st.rerun()
    else:
        st.warning("⚠️ ¿Estás seguro de que deseas reiniciar tus puntos y rachas de estudio?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Sí, deseo reiniciar todo", type="primary", use_container_width=True):
                db.query(UserStats).filter_by(user_id=u_id).delete()
                db.commit()
                st.session_state["confirm_delete_stats"] = False
                st.success("Estadísticas reiniciadas.")
                st.rerun()
        with col_no:
            if st.button("Cancelar", use_container_width=True):
                st.session_state["confirm_delete_stats"] = False
                st.rerun()

except Exception as e:
    st.error(f"Error cargando dashboard: {e}")
finally:
    db.close()


