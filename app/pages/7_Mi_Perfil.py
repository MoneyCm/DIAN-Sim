import streamlit as st
import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import func

# Add root to python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import User, UserStats, QuestionPerformance, Question, UserOPEC, Achievement
from ui_utils import load_css, render_header, metric_card
from core.auth import AuthManager
from core.rank_system import get_rank_info

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("⚠️ Por favor inicia sesión.")
    st.stop()

load_css()
render_header(title="Perfil del Aspirante", subtitle="Analítica avanzada de compatibilidad y maestría. Mikey")

u_id = st.session_state.get("user_id")
db = SessionLocal()

try:
    # 1. User Header Info
    stats = db.query(UserStats).filter_by(user_id=u_id).first()
    user = db.query(User).get(u_id)
    rank, next_rank = get_rank_info(stats.total_points if stats else 0)

    col_h1, col_h2 = st.columns([1, 3])

    with col_h1:
        st.markdown(f"""
        <div class="dian-card" style='text-align: center; padding: 30px;'>
            <div style='font-size: 5rem;'>{rank["icon"]}</div>
            <h2 style='margin: 10px 0;'>{user.username}</h2>
            <div style='background: {rank["color"]}; color: white; padding: 5px 15px; border-radius: 20px; display: inline-block; font-weight: 800;'>
                {rank["name"]}
            </div>
            <div style='margin-top: 15px; font-size: 0.9rem; color: var(--text-muted);'>
                Puntos Totales: <b>{stats.total_points if stats else 0}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_h2:
        st.markdown('<div class="dian-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("🚀 Tu Progreso hacia el siguiente nivel")
        if next_rank:
            diff = next_rank["threshold"] - stats.total_points
            st.markdown(f"Te faltan **{diff} puntos** para convertirte en **{next_rank['name']}** {next_rank['icon']}.")
            
            # Progress bar
            total_needed = next_rank["threshold"] - rank["threshold"]
            current_progress = stats.total_points - rank["threshold"]
            pct = min(100, int((current_progress / total_needed) * 100))
            st.progress(pct/100, text=f"{pct}% completado")
        else:
            st.success("¡Has alcanzado el rango máximo de Comisionado Elite! Mikey 👑")
        
        st.divider()
        st.subheader("🎖️ Logros Recientes")
        achievements = db.query(Achievement).filter_by(user_id=u_id).order_by(Achievement.unlocked_at.desc()).limit(4).all()
        if achievements:
            cols = st.columns(4)
            for i, ach in enumerate(achievements):
                with cols[i]:
                    st.markdown(f"<div style='text-align:center;'>{ach.icon}<br><small>{ach.name}</small></div>", unsafe_allow_html=True)
        else:
            st.info("Aún no has desbloqueado medallas. ¡Sigue entrenando!")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # 2. COMPETENCY ANALYTICS (RADAR)
    st.subheader("📊 Radar de Competencias (Maestría)")

    # Query performance joined with questions to get macro_dominio Mikey (Resilient v21)
    try:
        # Check if the class has the new attribute before querying
        m_attr = getattr(QuestionPerformance, "mastery_level", None)
        if m_attr is not None:
            perf_data = db.query(
                Question.macro_dominio, 
                func.avg(QuestionPerformance.mastery_level).label('avg_mastery')
            ).join(QuestionPerformance, Question.question_id == QuestionPerformance.question_id)\
             .filter(QuestionPerformance.user_id == u_id)\
             .group_by(Question.macro_dominio).all()
        else:
            perf_data = [] # Fallback safe Mikey
    except Exception as e:
        print(f"⚠️ Analítica Radar no disponible (Clase stale?): {e}")
        perf_data = []

    if perf_data:
        df_perf = pd.DataFrame(perf_data, columns=['Macro-Dominio', 'Nivel de Maestría'])
        
        col_rad1, col_rad2 = st.columns([2, 1])
        
        with col_rad1:
            fig = px.line_polar(df_perf, r='Nivel de Maestría', theta='Macro-Dominio', line_close=True,
                               color_discrete_sequence=['#E60000'])
            fig.update_traces(fill='toself')
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 10])
                ),
                showlegend=False,
                height=400,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col_rad2:
            st.markdown('<div class="dian-card">', unsafe_allow_html=True)
            st.subheader("🔍 Diagnóstico")
            mejor = df_perf.loc[df_perf['Nivel de Maestría'].idxmax()]
            peor = df_perf.loc[df_perf['Nivel de Maestría'].idxmin()]
            
            st.write(f"🌟 **Tu Fortaleza:** {mejor['Macro-Dominio']} ({mejor['Nivel de Maestría']:.1f}/10)")
            st.write(f"🛑 **Por mejorar:** {peor['Macro-Dominio']} ({peor['Nivel de Maestría']:.1f}/10)")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No hay suficientes datos para generar tu radar de competencias. Realiza más simulacros para ver tu analítica. Mikey")

    st.divider()

    # 3. AI IDONEITY REPORT (Fase 5 Final)
    st.subheader("🧠 Informe de Idoneidad (IA)")
    active_opec = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()

    if active_opec and perf_data:
        if st.button("✨ Generar Informe de Idoneidad con IA"):
            with st.spinner("La IA está analizando tu compatibilidad con el cargo..."):
                try:
                    from core.generators.llm import LLMGenerator
                    from core.config import get_api_key
                    
                    provider = st.session_state.get("current_provider", "Gemini")
                    api_key = get_api_key(provider)
                    
                    if api_key:
                        gen = LLMGenerator(provider, api_key)
                        # Prepare brief context for the AI
                        perf_str = ", ".join([f"{d[0]}: {d[1]:.1f}" for d in perf_data])
                        opec_str = f"Cargo: {active_opec.job_title}, Propósito: {active_opec.purpose}"
                        
                        prompt = f"""
                        Actúa como un Consultor de Selección Pro. Analiza el desempeño del aspirante y su cargo objetivo.
                        CARGO: {opec_str}
                        DESEMPEÑO ACTUAL: {perf_str} (sobre 10)
                        
                        PUNTOS CLAVE:
                        1. ¿Qué tan apto es para el cargo según sus fortalezas?
                        2. ¿Qué temas específicos debe reforzar para asegurar la vacante?
                        3. Da un mensaje motivador técnico.
                        
                        Mantén la respuesta en 3 párrafos impactantes. Mikey
                        """
                        
                        # We reuse explain_question or similar but let's call it directly or through a generic method if existed
                        # For now, let's assume it has a generic method or we just need the text
                        # We'll use a trick: explain_question with a custom prompt structure
                        report = gen.explain_question({"stem": prompt, "options_json": {}, "correct_key": "", "rationale": "Analizar idoneidad"})
                        
                        st.markdown(f'<div class="dian-card" style="border-left: 5px solid #3b82f6; background: rgba(59, 130, 246, 0.05);">{report}</div>', unsafe_allow_html=True)
                    else:
                        st.error("No se encontró API Key para generar el informe.")
                except Exception as e:
                    st.error(f"Error generando informe: {e}")
    elif not active_opec:
        st.warning("Selecciona una OPEC activa en la página de Cargos para recibir tu informe de idoneidad.")
    else:
        st.info("Necesitas realizar al menos un simulacro para que la IA analice tu perfil.")

except Exception as e:
    st.error(f"Error al cargar perfil tras conexión DB: {e}")
finally:
    db.close()
