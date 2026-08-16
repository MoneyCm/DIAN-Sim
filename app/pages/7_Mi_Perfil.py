import streamlit as st
import os
import sys
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import func

# Add root to python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import User, UserStats, QuestionPerformance, Question, UserOPEC, Achievement
from ui_utils import load_css, log_ui_exception, metric_card, render_header
from core.auth import AuthManager
from core.rank_system import get_rank_info
from core.competitions import get_active_competition_id

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("⚠️ Por favor inicia sesión.")
    st.stop()

load_css()
render_header(title="Perfil del aspirante", subtitle="Tu progreso y evidencia de desempeño en el concurso activo")

u_id = st.session_state.get("user_id")
db = SessionLocal()

try:
    # 1. User Header Info
    stats = db.query(UserStats).filter_by(user_id=u_id).first()
    user = db.query(User).get(u_id)
    active_competition_id = get_active_competition_id(db, u_id)
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
            st.success("¡Has alcanzado el rango máximo de Comisionado Elite! 👑")
        
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

    # 2. EVIDENCE-BASED COMPETENCY ANALYTICS
    st.subheader("📊 Evidencia de desempeño por dominio")

    try:
        raw_perf = db.query(
            Question.macro_dominio,
            func.sum(QuestionPerformance.hits).label("hits"),
            func.sum(QuestionPerformance.misses).label("misses"),
        ).join(QuestionPerformance, Question.question_id == QuestionPerformance.question_id).filter(
            QuestionPerformance.user_id == u_id,
            Question.competition_id == active_competition_id,
            Question.macro_dominio.isnot(None),
            Question.macro_dominio != "",
        ).group_by(Question.macro_dominio).all()
    except Exception as e:
        log_ui_exception("profile.analytics", e)
        raw_perf = []

    perf_rows = []
    for domain, hits, misses in raw_perf:
        hits, misses = int(hits or 0), int(misses or 0)
        attempts = hits + misses
        if attempts:
            perf_rows.append({"Dominio": domain, "Aciertos": hits, "Errores": misses,
                              "Intentos": attempts, "Precisión": hits / attempts * 100})

    total_domains = db.query(func.count(func.distinct(Question.macro_dominio))).filter(
        Question.competition_id == active_competition_id,
        Question.macro_dominio.isnot(None), Question.macro_dominio != "",
    ).scalar() or 0
    perf_data = [(row["Dominio"], row["Precisión"] / 10) for row in perf_rows]

    if perf_rows:
        df_perf = pd.DataFrame(perf_rows).sort_values("Precisión")
        col_chart, col_diagnosis = st.columns([2, 1])
        with col_chart:
            fig = go.Figure(go.Bar(
                x=df_perf["Precisión"], y=df_perf["Dominio"], orientation="h",
                marker_color=["#16a34a" if value >= 70 else "#dc2626" for value in df_perf["Precisión"]],
                customdata=df_perf[["Aciertos", "Errores", "Intentos"]],
                hovertemplate="%{y}<br>Precisión: %{x:.0f}%<br>Aciertos: %{customdata[0]}<br>Errores: %{customdata[1]}<br>Intentos: %{customdata[2]}<extra></extra>",
            ))
            fig.add_vline(x=70, line_dash="dash", line_color="#64748b")
            fig.update_xaxes(range=[0, 100], ticksuffix="%", title=None, fixedrange=True)
            fig.update_yaxes(title=None, fixedrange=True)
            fig.update_layout(height=max(260, 62 * len(df_perf)), margin=dict(l=10, r=15, t=20, b=20),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig, width="stretch", key="profile_domain_evidence")

        with col_diagnosis:
            st.subheader("🔍 Diagnóstico")
            best = max(perf_rows, key=lambda row: row["Precisión"])
            priority = min(perf_rows, key=lambda row: row["Precisión"])
            st.metric("Cobertura evaluada", f"{len(perf_rows)}/{total_domains or len(perf_rows)} dominios")
            st.success(f"Fortaleza observada: **{best['Dominio']}** · {best['Precisión']:.0f}% en {best['Intentos']} intentos.")
            if len(perf_rows) > 1 or priority["Precisión"] < 70:
                st.warning(f"Prioridad: **{priority['Dominio']}** · {priority['Precisión']:.0f}% en {priority['Intentos']} intentos.")
            if len(perf_rows) < total_domains:
                st.caption(f"Faltan {total_domains - len(perf_rows)} dominio(s) por evaluar; no se califican como debilidad hasta que respondas preguntas.")
    else:
        st.info("Aún no hay respuestas suficientes en este concurso para diagnosticar tu desempeño. Completa una sesión guiada o un simulacro; los dominios no evaluados no se mostrarán como debilidades.")

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
                    log_ui_exception("profile.report.generate", e)
                    st.error("No fue posible generar el informe.")
    elif not active_opec:
        st.warning("Selecciona una OPEC activa en la página de Cargos para recibir tu informe de idoneidad.")
    else:
        st.info("Necesitas realizar al menos un simulacro para que la IA analice tu perfil.")

except Exception as e:
    log_ui_exception("profile.load", e)
    st.error("No fue posible cargar el perfil. Intenta nuevamente.")
finally:
    db.close()
