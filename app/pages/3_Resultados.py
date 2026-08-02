import streamlit as st
import os, sys, datetime

# Add root to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# The instruction implies adding this block, but it already exists.
# If `import pandas as pd` was intended to be added, it would go here.
# For now, I will assume the instruction was to ensure the existing block is present.

from db.session import SessionLocal
from db.models import Question
from ui_utils import load_css, render_header, metric_card, render_custom_sidebar, render_favorite_button
from core.pdf_utils import generate_exam_pdf, generate_certificate_pdf
from core.legacy_question_audit import is_safe_for_active_study
from core.competitions import get_active_competition_id
from services.stats_service import StatsService

from core.auth import AuthManager

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión.")
    st.stop()

load_css()
render_custom_sidebar()
result_preview = st.session_state.get("last_results", {})
is_daily_session = result_preview.get("session_kind") == "daily"
render_header(
    title="Resumen del plan diario" if is_daily_session else "Resultados del Simulacro",
    subtitle=(
        "Lo aprendido hoy y los temas que debes reforzar"
        if is_daily_session else "Análisis de tu desempeño reciente"
    ),
)
# v2.5.1 - Fix PDF Binary

if "last_results" not in st.session_state:
    st.info("No hay resultados recientes para mostrar.")
    with st.container():
         if st.button("⬅️ Volver al Inicio"):
             st.switch_page("pages/6_Dashboard.py")
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
    st.warning(f"👑 ¡ASCENSO DE RANGO! Ahora eres: **{data['rank_up']}**")

total = data["total"]
correct = data["correct"]

# Status Message
if is_daily_session:
    daily_precision = (correct / total * 100) if total else 0
    st.success(
        f"✅ Sesión diaria completada: {correct} de {total} respuestas correctas "
        f"({daily_precision:.0f}%). Los errores ya quedaron programados para repaso."
    )
elif not is_passed:
    st.error("🚨 RESULTADO: NO SUPERADO (Módulo Funcional por debajo del 70%). Según el protocolo de la CNSC, esta prueba es eliminatoria.")
else:
    st.success("🎉 RESULTADO: SUPERADO. Has cumplido con el umbral mínimo del módulo funcional.")

# Metric Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    if is_daily_session:
        metric_card("Precisión de hoy", f"{daily_precision:.0f}%", f"{correct}/{total} correctas")
    else:
        metric_card("Puntaje Ponderado", f"{total_weighted:.1f}/100", f"Funcional: {f_pct:.0f}%")
with col2:
    metric_card("Puntos Ganados", f"+{data.get('points_earned', 0)}", "¡Buen trabajo!")
with col3:
    metric_card("Racha Actual", f"{data.get('new_streak', 0)}🔥", "Días seguidos")
with col4:
    if is_daily_session:
        metric_card("Plan diario", "COMPLETADO", "Continúa mañana")
    else:
        metric_card("Módulo Funcional", "ELIMINATORIO", "Aprobado" if is_passed else "Reprobado")


st.divider()

# Evidence-based reinforcement summary
st.subheader("🎯 Prioridades de refuerzo")
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
            st.markdown("##### 💡 Recomendación Inteligente:")
            top_weak = weak_skills[0]
            st.info(f"Deberías reforzar: **{top_weak.topic}**")
            
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
                    st.markdown(f"> **📖 Lectura Prioritaria:**  \n*{ref_q.source_refs}*")
                else:
                    st.markdown(f"El sistema ha detectado que este es tu punto más débil. Te sugerimos revisar la normativa asociada.")
                db_ref.close()
            except:
                pass
            
            if st.button("💊 Crear refuerzo de mi debilidad", key="btn_refuerzo", type="primary"):
                 source_context = ""
                 if 'ref_q' in locals() and ref_q:
                     source_context = f"{ref_q.source_refs or ''}\n{ref_q.rationale or ''}".strip()
                 st.session_state["ai_reinforcement_topic"] = top_weak.topic
                 st.session_state["ai_reinforcement_source_context"] = source_context
                 st.session_state["ai_default_topic"] = top_weak.topic
                 st.session_state["ai_default_diff"] = 3 if top_weak.mastery_score < 40 else 2
                 st.switch_page("pages/4_Generador_IA.py")
    else:
        st.info("Todavía no hay temas evaluados por debajo de la meta en este concurso.")
else:
    st.info("Inicia sesión para ver tu rastreo de debilidades.")

st.divider()

# --- v2.5 PDF DOWNLOAD BUTTON ---
st.subheader("📄 Reporte de Desempeño")
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

# Botones de Acción
col_b1, col_b2, col_b3 = st.columns(3)
with col_b1:
    st.button("📋 Detalle incluido abajo", disabled=True, use_container_width=True)
with col_b2:
    try:
        pdf_bytes = generate_exam_pdf(data, details)
        st.download_button("💾 Reporte PDF", data=pdf_bytes, file_name=f"Resultado_DIAN_{datetime.datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.error(f"Error PDF: {e}")
with col_b3:
    if is_daily_session:
        st.button("📚 Aprendizaje guardado", disabled=True, use_container_width=True)
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
            "🎓 Constancia de práctica",
            data=cert_pdf,
            file_name=f"Constancia_practica_{user_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="Documento personal de seguimiento; no es un certificado oficial de la DIAN ni de la CNSC.",
        )
    else:
        st.button("🎯 Meta: 70%", disabled=True, use_container_width=True, help="Supera el 70% ponderado para generar una constancia personal de práctica.")

st.divider()

if not is_passed and not is_daily_session:
    st.warning("🚨 El reporte PDF se generó, pero recuerda que no superaste el módulo eliminatorio Funcional.")
    st.info("💡 Te recomendamos generar un nuevo simulacro enfocado específicamente en tus debilidades del Eje Funcional.")
else:
    st.subheader("📝 Detalle de Respuestas")

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
                st.info(f"💡 **Explicación:** {q.rationale}")
            else:
                st.caption(f"💡 **Explicación:** {q.rationale}")
                
            st.caption(f"ID: {q.question_id} | Macro-Dominio: {q.macro_dominio} | Micro: {q.micro_competencia}")
            render_favorite_button(qid, user_id)
            st.markdown("</div>", unsafe_allow_html=True)

    db.close()

if st.button("🏠 Inicio", type="primary"):
    st.switch_page("pages/6_Dashboard.py")
