import streamlit as st
import os, sys, datetime
from collections import defaultdict
from zoneinfo import ZoneInfo

# Add root to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# The instruction implies adding this block, but it already exists.
# If `import pandas as pd` was intended to be added, it would go here.
# For now, I will assume the instruction was to ensure the existing block is present.

from db.session import SessionLocal
from db.models import Attempt, Question
from ui_utils import load_css, render_header, metric_card, render_custom_sidebar, render_favorite_button
from core.pdf_utils import generate_exam_pdf, generate_certificate_pdf
from core.legacy_question_audit import is_safe_for_active_study
from core.competitions import get_active_competition_id
from services.stats_service import StatsService

from core.auth import AuthManager
from core.session_results import load_last_result, load_result_history

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesiÃ³n.")
    st.stop()

load_css()
render_custom_sidebar()
result_preview = st.session_state.get("last_results", {})
if not result_preview:
    _result_db = SessionLocal()
    try:
        result_preview = load_last_result(_result_db, st.session_state.get("user_id")) or {}
        if result_preview:
            st.session_state["last_results"] = result_preview
    finally:
        _result_db.close()
if not result_preview:
    _result_db = SessionLocal()
    try:
        result_preview = load_last_result(_result_db, st.session_state.get("user_id")) or {}
        if result_preview:
            st.session_state["last_results"] = result_preview
    finally:
        _result_db.close()
is_daily_session = result_preview.get("session_kind") == "daily"
has_recent_result = bool(result_preview)
render_header(
    title=(
        "Resumen del plan diario" if is_daily_session
        else "Resultados del simulacro" if has_recent_result
        else "Resultados y progreso"
    ),
    subtitle=(
        "Lo aprendido hoy y los temas que debes reforzar"
        if is_daily_session else "AnÃ¡lisis de tu desempeÃ±o reciente"
    ),
)
# v2.5.1 - Fix PDF Binary

if not result_preview:
    user_id = st.session_state.get("user_id")
    history_db = SessionLocal()
    try:
        active_competition_id = get_active_competition_id(history_db, user_id)
        attempts = history_db.query(Attempt).join(Question).filter(
            Attempt.user_id == user_id,
            Question.competition_id == active_competition_id,
        ).order_by(Attempt.created_at.desc()).all()

        if not attempts:
            st.info(
                "TodavÃ­a no hay intentos guardados en este concurso. Completa el plan diario "
                "o una prÃ¡ctica para comenzar tu historial."
            )
        else:
            total_attempts = len(attempts)
            total_correct = sum(1 for item in attempts if item.is_correct)
            overall_accuracy = total_correct / total_attempts * 100
            practiced_questions = len({item.question_id for item in attempts})
            error_count = total_attempts - total_correct
            metric_cols = st.columns(4)
            metric_cols[0].metric("Intentos guardados", total_attempts)
            metric_cols[1].metric("PrecisiÃ³n acumulada", f"{overall_accuracy:.0f}%")
            metric_cols[2].metric("Preguntas practicadas", practiced_questions)
            metric_cols[3].metric("Errores para aprender", error_count)

            bogota = ZoneInfo("America/Bogota")
            daily = defaultdict(lambda: {"correct": 0, "total": 0})
            for item in attempts:
                created_at = item.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=datetime.timezone.utc)
                day = created_at.astimezone(bogota).date()
                daily[day]["total"] += 1
                daily[day]["correct"] += int(bool(item.is_correct))
            recent_days = sorted(daily.items(), reverse=True)[:7]
            st.subheader("ðŸ“… Ãšltimos dÃ­as con actividad")
            history_rows = [{
                "Fecha": day.strftime("%d/%m/%Y"),
                "Preguntas": values["total"],
                "Correctas": values["correct"],
                "PrecisiÃ³n": f"{values['correct'] / values['total'] * 100:.0f}%",
            } for day, values in recent_days]
            st.dataframe(history_rows, hide_index=True, width="stretch")
            st.caption(
                "Este historial permanece aunque cierres sesiÃ³n o cambies de dispositivo. "
                "El detalle pregunta por pregunta aparece inmediatamente al terminar una sesiÃ³n."
            )
    finally:
        history_db.close()

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("ðŸŽ¯ Continuar plan diario", type="primary", use_container_width=True):
            st.switch_page("pages/6_Dashboard.py")
    with action_cols[1]:
        if st.button("▶️ Iniciar práctica", use_container_width=True):
            st.switch_page("pages/1_Nuevo_Simulacro.py")
    st.stop()

data = st.session_state["last_results"]
is_daily_session = data.get("session_kind") == "daily"
breakdown = data.get("breakdown", {})
is_passed = data.get("is_passed", True)

# --- v2.6 WEIGHTED CALCULATION ---
# Funcional (60%), Comportamental (20%), Integridad (20%)
f_c, f_t = breakdown.get("FUNCIONAL", (0, 0))
f_pct = (f_c / f_t * 100) if f_t > 0 else 0
f_weighted = (f_c / f_t * 60) if f_t > 0 else 0

c_c, c_t = breakdown.get("COMPORTAMENTAL", (0, 0))
c_weighted = (c_c / c_t * 20) if c_t > 0 else 0

i_c, i_t = breakdown.get("INTEGRIDAD", (0, 0))
i_weighted = (i_c / i_t * 20) if i_t > 0 else 0

total_weighted = f_weighted + c_weighted + i_weighted

# --- v2.5 CELEBRATION LOGIC ---
if data.get("new_achievements"):
    st.balloons()
    for ach in data["new_achievements"]:
        st.success(f"🏆 ¡LOGRO DESBLOQUEADO: **{ach}**!")

if data.get("rank_up"):
    st.snow()
    st.warning(f"🎉 ¡ASCENSO DE RANGO! Ahora eres: **{data['rank_up']}**")

total = data["total"]
correct = data["correct"]

# Status Message
if is_daily_session:
    daily_precision = (correct / total * 100) if total else 0
    st.progress(1.0, text="Paso 3 de 3 · Cierre y programación del próximo repaso")
    st.success(
        f"✅ Sesión diaria completada: {correct} de {total} respuestas correctas "
        f"({daily_precision:.0f}%). Los errores ya quedaron programados para repaso."
    )
elif not is_passed:
    st.error("ðŸš¨ RESULTADO: NO SUPERADO (MÃ³dulo Funcional por debajo del 70%). SegÃºn el protocolo de la CNSC, esta prueba es eliminatoria.")
else:
    st.success("ðŸŽ‰ RESULTADO: SUPERADO. Has cumplido con el umbral mÃ­nimo del mÃ³dulo funcional.")

# Metric Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    if is_daily_session:
        metric_card("PrecisiÃ³n de hoy", f"{daily_precision:.0f}%", f"{correct}/{total} correctas")
    else:
        metric_card("Puntaje Ponderado", f"{total_weighted:.1f}/100", f"Funcional: {f_pct:.0f}%")
with col2:
    metric_card("Puntos Ganados", f"+{data.get('points_earned', 0)}", "¡Buen trabajo!")
with col3:
    metric_card("Racha Actual", f"{data.get('new_streak', 0)}ðŸ”¥", "DÃ­as seguidos")
with col4:
    if is_daily_session:
        duration_minutes = max(1, round(int(data.get("duration_seconds", 0)) / 60))
        metric_card("Tiempo activo", f"{duration_minutes} min", "Plan completado")
    else:
        metric_card("MÃ³dulo Funcional", "ELIMINATORIO", "Aprobado" if is_passed else "Reprobado")


st.divider()

with st.expander("Historial de sesiones recientes", expanded=False):
    history_db = SessionLocal()
    try:
        session_history = load_result_history(history_db, st.session_state.get("user_id"))
    finally:
        history_db.close()
    if not session_history:
        st.caption("El historial aparecerá después de completar la próxima sesión.")
    else:
        history_rows = []
        for item in reversed(session_history[-10:]):
            item_total = int(item.get("total", 0) or 0)
            item_correct = int(item.get("correct", 0) or 0)
            history_rows.append({
                "Fecha": str(item.get("saved_at", ""))[:16].replace("T", " "),
                "Tipo": "Plan diario" if item.get("session_kind") == "daily" else "Simulacro",
                "Tiempo": f"{max(1, round(int(item.get('duration_seconds', 0) or 0) / 60))} min",
                "Preguntas": item_total,
                "Precisión": f"{(item_correct / item_total * 100):.0f}%" if item_total else "—",
            })
        st.dataframe(history_rows, hide_index=True, use_container_width=True)

# Evidence-based reinforcement summary
st.subheader("ðŸŽ¯ Prioridades de refuerzo")
user_id = st.session_state.get("user_id")
if user_id:
    scope_db = SessionLocal()
    active_competition_id = get_active_competition_id(scope_db, user_id)
    scope_db.close()
    weak_skills = StatsService.get_weakest_topics(
        user_id, limit=3, competition_id=active_competition_id
    )
    
    if weak_skills:
        c_radar, c_recommend = st.columns([1, 1])
        with c_radar:
            st.markdown("##### Temas que conviene reforzar")
            for w in weak_skills:
                st.markdown(f"**{w.topic}** ({w.mastery_score:.0f}%)")
                st.progress(int(max(w.mastery_score, 0)) / 100)
                
        with c_recommend:
            st.markdown("##### ðŸ’¡ RecomendaciÃ³n Inteligente:")
            top_weak = weak_skills[0]
            st.info(f"DeberÃ­as reforzar: **{top_weak.topic}**")
            
            # Smart Source Lookup
            try:
                # Find a reference from the bank for this topic
                db_ref = SessionLocal()
                topic_refs = db_ref.query(Question).filter(
                    Question.competition_id == active_competition_id,
                    Question.topic == top_weak.topic,
                    Question.source_refs != None,
                ).all()
                ref_q = next((item for item in topic_refs if is_safe_for_active_study(item)), None)
                if ref_q and ref_q.source_refs:
                    st.markdown(f"> **ðŸ“– Lectura Prioritaria:**  \n*{ref_q.source_refs}*")
                else:
                    st.markdown(f"El sistema ha detectado que este es tu punto mÃ¡s dÃ©bil. Te sugerimos revisar la normativa asociada.")
                db_ref.close()
            except:
                pass
            
            if st.button("▶️ Practicar esta debilidad", key="btn_refuerzo", type="primary"):
                 st.session_state["practice_recommended_topic"] = top_weak.topic
                 st.switch_page("pages/1_Nuevo_Simulacro.py")
    else:
        st.info("TodavÃ­a no hay temas evaluados por debajo de la meta en este concurso.")
else:
    st.info("Inicia sesiÃ³n para ver tu rastreo de debilidades.")

st.divider()

# --- v2.5 PDF DOWNLOAD BUTTON ---
st.subheader("ðŸ“„ Reporte de DesempeÃ±o")
db = SessionLocal()
q_ids = data["q_ids"]
answers = st.session_state.get("answers", {})

details = []
for qid in q_ids:
    q = db.query(Question).get(qid)
    details.append({
        "stem": q.stem,
        "user_ans": answers.get(qid, "N/A"),
        "correct_key": q.correct_key,
        "rationale": q.rationale
    })

# Botones de AcciÃ³n
col_b1, col_b2, col_b3 = st.columns(3)
with col_b1:
    st.button("ðŸ“‹ Detalle incluido abajo", disabled=True, use_container_width=True)
with col_b2:
    try:
        pdf_bytes = generate_exam_pdf(data, details)
        st.download_button("ðŸ’¾ Reporte PDF", data=pdf_bytes, file_name=f"Resultado_DIAN_{datetime.datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.error(f"Error PDF: {e}")
with col_b3:
    if is_daily_session:
        st.button("ðŸ“š Aprendizaje guardado", disabled=True, use_container_width=True)
    elif total_weighted >= 70:
        user_name = st.session_state.get("username", "Aspirante")
        from db.models import UserOPEC
        db_o = SessionLocal()
        u_id = st.session_state.get("user_id")
        active_opec = db_o.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
        o_title = active_opec.job_title if active_opec else "Simulacro General"
        db_o.close()
        
        cert_pdf = generate_certificate_pdf(user_name, o_title, total_weighted)
        st.download_button(
            "ðŸŽ“ Constancia de prÃ¡ctica",
            data=cert_pdf,
            file_name=f"Constancia_practica_{user_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="Documento personal de seguimiento; no es un certificado oficial de la DIAN ni de la CNSC.",
        )
    else:
        st.button("ðŸŽ¯ Meta: 70%", disabled=True, use_container_width=True, help="Supera el 70% ponderado para generar una constancia personal de prÃ¡ctica.")

st.divider()

if not is_passed and not is_daily_session:
    st.warning("ðŸš¨ El reporte PDF se generÃ³, pero recuerda que no superaste el mÃ³dulo eliminatorio Funcional.")
    st.info("ðŸ’¡ Te recomendamos generar un nuevo simulacro enfocado especÃ­ficamente en tus debilidades del Eje Funcional.")
else:
    st.subheader("ðŸ“ Detalle de Respuestas")

    db = SessionLocal()
    q_ids = data["q_ids"]
    answers = st.session_state.get("answers", {})

    for i, qid in enumerate(q_ids):
        q = db.query(Question).get(qid)
        user_ans = answers.get(qid, "N/A")
        is_right = (user_ans == q.correct_key)
        
        icon = "✅" if is_right else "❌"
        color_class = "color: #4CAF50" if is_right else "color: #D90000"
        
        with st.expander(f"{icon} Pregunta {i+1}: {q.topic}"):
            st.markdown(f"<div class='dian-card' style='border:none; padding:0;'>", unsafe_allow_html=True)
            st.markdown(f"**Enunciado:** {q.stem}")
            
            col_ans1, col_ans2 = st.columns(2)
            
            # Get option texts
            opts = q.options_json if q.options_json else {}
            user_text = opts.get(user_ans, "Sin responder")
            correct_text = opts.get(q.correct_key, "")

            with col_ans1:
                st.markdown(f"**Tu respuesta:** <span style='{color_class}; font-weight:bold;'>{user_ans}) {user_text}</span>", unsafe_allow_html=True)
            with col_ans2:
                st.markdown(f"**Correcta:** <span style='color: #4CAF50; font-weight:bold;'>{q.correct_key}) {correct_text}</span>", unsafe_allow_html=True)
            
            st.markdown("---")
            if not is_right:
                st.info(f"ðŸ’¡ **ExplicaciÃ³n:** {q.rationale}")
            else:
                st.caption(f"ðŸ’¡ **ExplicaciÃ³n:** {q.rationale}")
                
            st.caption(f"ID: {q.question_id} | Macro-Dominio: {q.macro_dominio} | Micro: {q.micro_competencia}")
            render_favorite_button(qid, user_id)
            st.markdown("</div>", unsafe_allow_html=True)

    db.close()

if st.button("ðŸ  Inicio", type="primary"):
    st.switch_page("pages/6_Dashboard.py")



