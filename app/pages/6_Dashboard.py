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
from db.models import User, Skill, Attempt, Achievement, UserStats, UserOPEC, QuestionPerformance, Question, CaseStudy
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from ui_utils import load_css, render_header
import datetime, io

from core.auth import AuthManager
from core.rank_system import get_rank_info
from core.anki import generate_anki_deck

# pass # Removed st.set_page_config

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión en la página principal.")
    st.stop()

load_css()
render_header(title="Panel de Control", subtitle="Analítica de progreso y gamificación")

db = SessionLocal()

# --- AUTO-HEALING DB SCHEMA (NATIVE SQLITE3 - ROBUST) ---
try:
    import sqlite3
    
    # Calculate path relative to this file
    # app/pages/6_Dashboard.py -> app/pages -> app -> root -> dian_sim.db
    # This matches the session.py logic: os.path.dirname(__file__)/../../dian_sim.db
    db_path_fix = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'dian_sim.db'))
    
    # Connect directly
    conn_fix = sqlite3.connect(db_path_fix, timeout=10)
    cursor_fix = conn_fix.cursor()
    
    # 1. Check user_stats columns
    try:
        cursor_fix.execute("SELECT last_ia_date FROM user_stats LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor_fix.execute("ALTER TABLE user_stats ADD COLUMN last_ia_date TIMESTAMP")
            conn_fix.commit()
            st.toast("✅ DB fixed: last_ia_date")
        except: pass

    try:
        cursor_fix.execute("SELECT ia_count_today FROM user_stats LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor_fix.execute("ALTER TABLE user_stats ADD COLUMN ia_count_today INTEGER DEFAULT 0")
            conn_fix.commit()
            st.toast("✅ DB fixed: ia_count_today")
        except: pass
        
    # 2. Check question_performance columns
    try:
        cursor_fix.execute("SELECT is_favorite FROM question_performance LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor_fix.execute("ALTER TABLE question_performance ADD COLUMN is_favorite BOOLEAN DEFAULT 0")
            cursor_fix.execute("ALTER TABLE question_performance ADD COLUMN mastery_level FLOAT DEFAULT 0.0")
            cursor_fix.execute("ALTER TABLE question_performance ADD COLUMN is_mastered BOOLEAN DEFAULT 0")
            conn_fix.commit()
            st.toast("✅ DB fixed: question_performance")
        except: pass

    # 3. Check skills columns (THE CRITICAL ONE)
    try:
        cursor_fix.execute("SELECT user_id FROM skills LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor_fix.execute("ALTER TABLE skills ADD COLUMN user_id INTEGER")
            cursor_fix.execute("ALTER TABLE skills ADD COLUMN macro_dominio VARCHAR")
            cursor_fix.execute("ALTER TABLE skills ADD COLUMN micro_competencia VARCHAR")
            cursor_fix.execute("ALTER TABLE skills ADD COLUMN priority_weight FLOAT DEFAULT 1.0")
            conn_fix.commit()
            st.toast("✅ DB fixed: skills structure")
        except Exception as e:
             st.error(f"Native SQL fix failed for skills: {e}")

    conn_fix.close()

except Exception as e:
    st.error(f"Auto-healing critical error: {e}")
# -----------------------------------------------------

try:
    # 0. OPEC Goal (NEW Fase 2)
    u_id = st.session_state.get("user_id")
    
    active_opec = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
    
    # DEBUG LINE
    # st.write(f"🔍 DEBUG DASHBOARD: User {u_id} | Active OPEC found: {active_opec}")
    
    if active_opec:
        st.markdown(f"""
        <div style="background: rgba(230, 0, 0, 0.05); border-left: 5px solid var(--dian-red); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <span style="font-size: 0.8rem; color: #666; font-weight: bold; text-transform: uppercase;">Meta Activa: OPEC {active_opec.opec_number}</span><br>
            <span style="font-size: 1.2rem; font-weight: 800; color: #1e293b;">{active_opec.job_title}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ No has configurado una OPEC. Ve a 'Configuración OPEC' para enfocar tu estudio.")
        st.caption(f"Debug: No active OPEC found for user_id={u_id}")

    # 1. User Stats & Mastery
    stats = db.query(UserStats).filter_by(user_id=u_id).first()
    if not stats:
        stats = UserStats(user_id=u_id, current_streak=0, max_streak=0, total_points=0)

    # Mastery Calculation Mikey (Resilient v22)
    mastered_qs = 0
    total_qs = 0
    try:
        total_qs = db.query(QuestionPerformance).filter_by(user_id=u_id).count()
        if hasattr(QuestionPerformance, "is_mastered"):
            mastered_qs = db.query(QuestionPerformance).filter_by(user_id=u_id, is_mastered=True).count()
        else:
            # Fallback: estimate mastery if field is missing Mikey
            mastered_qs = 0 
    except Exception as e:
        print(f"⚠️ Error en Mastery Calculation: {e}")

    mastery_pct = (mastered_qs / total_qs * 100) if total_qs > 0 else 0

    # Quality Metrics v32 Mikey
    total_bank = db.query(Question).count()
    verified_bank = db.query(Question).filter_by(is_verified=True).count()
    quality_idx = (verified_bank / total_bank * 100) if total_bank > 0 else 0

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("🔥 Racha Actual", f"{stats.current_streak} días")
    with col_s2:
        st.metric("🎓 Maestría Real", f"{mastery_pct:.1f}%", f"{mastered_qs}/{total_qs} Qs")
    with col_s3:
        st.metric("🏆 Puntos Totales", f"{stats.total_points} pts")
    with col_s4:
        fav_count = db.query(QuestionPerformance).filter_by(user_id=u_id, is_favorite=True).count()
        st.metric("⭐ Favoritas", f"{fav_count} Qs", "Para repasar")

    # Quality Indicator Mikey
    st.markdown(f"""
    <div style="background: rgba(44, 62, 80, 0.05); border-radius: 10px; padding: 10px; margin-top: 10px; border-left: 5px solid #4CAF50;">
        <span style="font-size: 0.8rem; font-weight: 700;">ÍNDICE DE CALIDAD DEL BANCO: {quality_idx:.0f}%</span>
        <div style="background: #e0e0e0; height: 6px; border-radius: 3px; margin-top: 5px;">
            <div style="background: #4CAF50; width: {quality_idx}%; height: 100%; border-radius: 3px;"></div>
        </div>
        <small style="color: #666;">{verified_bank} de {total_bank} preguntas auditadas y certificadas con IA.</small>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 2. Balance Global y Progreso por Eje
    col_b1, col_b2 = st.columns([1, 2])

    with col_b1:
        st.markdown('<div class="dian-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("📊 Balance Global")
        total_hits = db.query(func.sum(QuestionPerformance.hits)).filter_by(user_id=u_id).scalar() or 0
        total_misses = db.query(func.sum(QuestionPerformance.misses)).filter_by(user_id=u_id).scalar() or 0
        
        if total_hits + total_misses > 0:
            fig_pie = px.pie(
                names=['Aciertos', 'Fallos'],
                values=[total_hits, total_misses],
                color=['Aciertos', 'Fallos'],
                color_discrete_map={'Aciertos': '#10b981', 'Fallos': '#ef4444'},
                hole=0.6
            )
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)')
            fig_pie.add_annotation(text=f"{int((total_hits/(total_hits+total_misses))*100)}%", showarrow=False, font_size=20, font_weight="bold")
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown(f"<p style='text-align:center; color:gray;'>{total_hits} Acertadas / {total_misses} Falladas</p>", unsafe_allow_html=True)
        else:
            st.info("No hay datos de intentos.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b2:
        st.markdown('<div class="dian-card" style="height: 100%;">', unsafe_allow_html=True)
        st.subheader("🎯 Nivel de Dominio por Eje")
        skills = db.query(Skill).filter_by(user_id=u_id).all()
        if skills:
            df_skills = pd.DataFrame([{
                'Eje': s.track,
                'Macro-Dominio': getattr(s, 'macro_dominio', "Transversal") or "Transversal",
                'Micro-Competencia': getattr(s, 'micro_competencia', s.topic) or s.topic,
                'Dominio': s.mastery_score
            } for s in skills])
            
            fig = px.sunburst(df_skills, path=['Eje', 'Macro-Dominio', 'Micro-Competencia'], values='Dominio',
                          color='Dominio', color_continuous_scale='RdYlGn',
                          range_color=[0, 100])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("¡Realiza tu primer simulacro!")
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. Rendimiento en el Tiempo
    st.markdown('<div class="dian-card">', unsafe_allow_html=True)
    st.subheader("📈 Rendimiento de los últimos intentos")
    attempts = db.query(Attempt).filter_by(user_id=u_id).order_by(Attempt.created_at.desc()).limit(50).all()
    if attempts:
        df_att = pd.DataFrame([{
            'Fecha': a.created_at,
            'Resultado': 1 if a.is_correct else 0
        } for a in attempts])
        
        # Agrupar por fecha
        df_att['Fecha'] = df_att['Fecha'].dt.date
        df_daily = df_att.groupby('Fecha').agg({'Resultado': 'mean'}).reset_index()
        df_daily['Porcentaje'] = df_daily['Resultado'] * 100
        
        fig_line = px.line(df_daily, x='Fecha', y='Porcentaje', title="Precisión Diaria (%)",
                           markers=True, line_shape='spline')
        fig_line.update_yaxes(range=[0, 105])
        fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_line, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. Radar de Habilidades & Refuerzo
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.subheader("🛡️ Radar de Macro-Dominios")
        if skills:
            avg_competencies = df_skills.groupby('Macro-Dominio')['Dominio'].mean().reset_index()
            fig_radar = go.Figure()
            # Actual Mastery
            fig_radar.add_trace(go.Scatterpolar(
                r=avg_competencies['Dominio'],
                theta=avg_competencies['Macro-Dominio'],
                fill='toself',
                name='Dominio Actual',
                line_color='#2c3e50',
                fillcolor='rgba(44, 62, 80, 0.3)'
            ))
            # Target Mastery (Ideal 90%)
            fig_radar.add_trace(go.Scatterpolar(
                r=[70] * len(avg_competencies),
                theta=avg_competencies['Macro-Dominio'],
                name='Umbral Aprobación (70%)',
                line_color='rgba(230, 0, 0, 0.5)',
                line_dash='dot'
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                margin=dict(l=40, r=40, t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        else:
            st.info("Sin datos para el radar.")

    with col_d2:
        st.subheader("⚠️ Habilidades a Reforzar")
        if skills:
            top_weak = db.query(Skill).filter_by(user_id=u_id).order_by(Skill.mastery_score.asc()).limit(5).all()
            for s in top_weak:
                color = "red" if s.mastery_score < 40 else "orange"
                st.markdown(f"""
                <div style="background: white; border-left: 5px solid {color}; padding: 10px; border-radius: 8px; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                    <b style="color: #333;">{s.topic}</b><br>
                    <span style="font-size: 0.8rem; color: #666;">{s.competency} | Dominio: {s.mastery_score:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay sugerencias todavía.")

    # 5. Vitrina de Trofeos y Ranking Global
    col_v1, col_v2 = st.columns([2, 1])

    with col_v1:
        st.markdown('<div class="dian-card">', unsafe_allow_html=True)
        st.subheader("🏆 Tu Vitrina de Trofeos")

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
            st.write("Aún no tienes trofeos. ¡Sigue estudiando para desbloquearlos!")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_v2:
        st.markdown('<div class="dian-card">', unsafe_allow_html=True)
        st.subheader("🥇 Ranking Global")
        
        # Pre-fetch for ranking
        all_stats = db.query(UserStats).join(User).order_by(UserStats.total_points.desc()).limit(10).all()
        
        for i, s in enumerate(all_stats):
            is_me = s.user_id == u_id
            bg = "rgba(230, 0, 0, 0.1)" if is_me else "transparent"
            icon = ["🥇", "🥈", "🥉"][i] if i < 3 else "🎖️"
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 5px 10px; border-radius: 5px; background: {bg}; border-bottom: 1px solid rgba(0,0,0,0.05);">
                <span>{icon} {s.user.username}</span>
                <span style="font-weight: 800;">{s.total_points} PTS</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 6. Herramientas Administrativas
    st.divider()
    st.subheader("🛠️ Herramientas de Exportación")

    all_qs = db.query(Question).all()

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
                file_name=f"Banco_Preguntas_DIAN_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
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

    else:
        st.warning("El banco está vacío. No hay datos para exportar.")

    st.divider()
    st.subheader("🎴 Exportar a Anki (Flashcards)")
    st.markdown("""
    Exporta tus **preguntas falladas** o **favoritas** para importarlas a **Anki** y repasar de forma espaciada.
    El archivo generado es un CSV estructurado con formato HTML para que tus tarjetas se vean limpias y profesionales en la aplicación.
    """)

    # 1. Obtener preguntas falladas (Intentos incorrectos) - Obteniendo IDs primero para evitar DISTINCT sobre columnas JSON en Postgres
    failed_q_ids = db.query(Attempt.question_id).filter(
        Attempt.user_id == u_id,
        Attempt.is_correct == False
    ).distinct().all()
    failed_q_ids = [r[0] for r in failed_q_ids]
    failed_qs = db.query(Question).options(joinedload(Question.case_study)).filter(Question.question_id.in_(failed_q_ids)).all() if failed_q_ids else []

    # 2. Obtener preguntas favoritas
    fav_q_ids = db.query(QuestionPerformance.question_id).filter(
        QuestionPerformance.user_id == u_id,
        QuestionPerformance.is_favorite == True
    ).distinct().all()
    fav_q_ids = [r[0] for r in fav_q_ids]
    fav_qs = db.query(Question).options(joinedload(Question.case_study)).filter(Question.question_id.in_(fav_q_ids)).all() if fav_q_ids else []

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
                    file_name=f"Anki_Dian_Fallas_Std_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
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
                    file_name=f"Anki_Dian_Favoritas_Std_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
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
                        "Norma": q.source_refs or ''
                    })
                
                # Generar mazo APKG
                try:
                    failed_apkg = generate_anki_deck(failed_dicts, "DIAN - Fallas Interactivas")
                    st.download_button(
                        label="📥 Descargar Mazo APKG (Anki Directo)",
                        data=failed_apkg,
                        file_name=f"DIAN_Fallas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.apkg",
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
                    file_name=f"Anki_Dian_Fallas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.csv",
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
                        "Norma": q.source_refs or ''
                    })
                
                # Generar mazo APKG
                try:
                    fav_apkg = generate_anki_deck(fav_dicts, "DIAN - Favoritas Interactivas")
                    st.download_button(
                        label="📥 Descargar Mazo APKG (Anki Directo)",
                        data=fav_apkg,
                        file_name=f"DIAN_Favoritas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.apkg",
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
                    file_name=f"Anki_Dian_Favoritas_Interactivas_{datetime.date.today().strftime('%Y%m%d')}.csv",
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
