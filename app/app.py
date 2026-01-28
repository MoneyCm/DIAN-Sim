import streamlit as st
import sys
import os

# Add root to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import SessionLocal
from db.models import User, UserOPEC, Attempt, UserStats, Achievement, Skill, QuestionPerformance, Configuration, Question
from ui_utils import load_css, render_header
from core.auth import AuthManager
from core.rank_system import get_rank_info

st.set_page_config(
    page_title="DIAN Sim - Simulador Oficial",
    page_icon="🇨🇴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FASE 3: LOGIN SYSTEM ---
# --- ANTI-BUG CLOUD: Limpiar modelos obsoletos de la sesión ---
if st.session_state.get("current_model") == "gemini-1.5-flash":
    st.session_state["current_model"] = "gemini-flash-latest"
if st.session_state.get("current_model") == "models/gemini-1.5-flash":
    st.session_state["current_model"] = "models/gemini-flash-latest"

if not AuthManager.check_auth():
    load_css()
    render_header(title="Acceso al Simulador", subtitle="Identifícate para continuar tu preparación")
    
    col_l1, col_l2 = st.columns([1, 1])
    
    with col_l1:
        st.markdown('<div class="dian-card">', unsafe_allow_html=True)
        st.subheader("🔑 Iniciar Sesión")
        with st.form("login_form"):
            user_in = st.text_input("Usuario")
            pass_in = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)
            
            if btn_login:
                try:
                    if AuthManager.login(user_in, pass_in):
                        st.success("¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
                except Exception as e:
                    import traceback
                    st.error(f"❌ Error de Sistema: Consulta los Logs para más detalle.")
                    print(f"🔥 FULL ERROR TRACEBACK:\n{traceback.format_exc()}")
                    # Intentar re-configurar mapeos si falló algo
                    try:
                        from sqlalchemy.orm import configure_mappers
                        configure_mappers()
                    except Exception as ce:
                        print(f"🔥 Mapper Configuration Error: {ce}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_l2:
        st.markdown('<div class="dian-card">', unsafe_allow_html=True)
        st.subheader("📝 Registrarse")
        st.info("¿Aún no tienes cuenta? Crea una para guardar tus 5 cargos (OPECs).")
        with st.form("register_form"):
            new_user = st.text_input("Nuevo Usuario")
            new_pass = st.text_input("Contraseña", type="password")
            confirm_pass = st.text_input("Confirmar Contraseña", type="password")
            btn_reg = st.form_submit_button("Crear Cuenta", use_container_width=True)
            
            if btn_reg:
                if not new_user or not new_pass:
                    st.error("Completa todos los campos")
                elif new_pass != confirm_pass:
                    st.error("Las contraseñas no coinciden")
                else:
                    db = SessionLocal()
                    if db.query(User).filter_by(username=new_user).first():
                        st.error("El usuario ya existe")
                        db.close()
                    else:
                        try:
                            hashed = AuthManager.hash_password(new_pass)
                            user = User(username=new_user, password_hash=hashed)
                            db.add(user)
                            db.commit()
                            st.success("Cuenta creada. ¡Ya puedes entrar!")
                        except Exception as e:
                            st.error(f"Error al registrar: {e}")
                        finally:
                            db.close()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop() # Stop execution here if not logged in

# --- v2.0 NEW: Sidebar Gamification Info ---
db_s = SessionLocal()
u_id = st.session_state.get("user_id")
stats_s = None
rank = {"name": "Aspirante", "icon": "🎓", "color": "#475569", "threshold": 0}
next_rank = None
pct = 0

try:
    if not stats_s:
        # Create stats for new user if not exist
        stats_s = UserStats(user_id=u_id, current_streak=0, max_streak=0, total_points=0)
        db_s.add(stats_s)
        db_s.commit()
        db_s.refresh(stats_s)
    
    if stats_s:
        rank, next_rank = get_rank_info(stats_s.total_points)
        
        # Calculate progress to next rank
        if next_rank:
            total_needed = next_rank["threshold"] - rank["threshold"]
            current_progress = stats_s.total_points - rank["threshold"]
            pct = min(100, int((current_progress / total_needed) * 100))
        else:
            pct = 100
            
        st.sidebar.markdown(f"""
<div class="dian-card" style='padding: 20px; text-align: center; margin-bottom: 5px; border-top: 3px solid {rank["color"]};'>
    <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 800; text-transform: uppercase; letter-spacing: 2px;'>Rango Actual</div>
    <div style='font-size: 2.5rem; margin: 5px 0;'>{rank["icon"]}</div>
    <div style='font-size: 1.1rem; font-weight: 800; color: {rank["color"]}; margin-bottom: 5px;'>{rank["name"]}</div>
    <div style='background: rgba(0,0,0,0.05); height: 8px; border-radius: 4px; margin: 10px 0; overflow: hidden;'>
        <div style='background: {rank["color"]}; width: {pct}%; height: 100%; transition: width 0.5s ease;'></div>
    </div>
    <div style='font-size: 0.7rem; color: var(--text-muted);'>
        {stats_s.total_points} / {next_rank["threshold"] if next_rank else "MAX"} PTS
    </div>
</div>
""", unsafe_allow_html=True)

        # Categorización Visual en el Sidebar v6.0
        st.sidebar.markdown('<div class="sidebar-category">🚀 Mi Entrenamiento</div>', unsafe_allow_html=True)
        # (Simulacro, Resultados, Banco - Rendered by pages/)
        
        st.sidebar.markdown('<div class="sidebar-category">🛠️ Herramientas AI</div>', unsafe_allow_html=True)
        # (Generador, Auditor - Rendered by pages/)

        st.sidebar.markdown('<div class="sidebar-category">⚙️ Configuración</div>', unsafe_allow_html=True)
        # (OPEC, Perfil - Rendered by pages/)
        
    st.sidebar.button("🚪 Cerrar Sesión", on_click=AuthManager.logout, use_container_width=True)
except Exception as e:
    st.sidebar.error(f"⚠️ Error: {e}")
db_s.close()


# Inject Global CSS
load_css()

# Render Custom Header
render_header()

# Introduction / Hero Dashboard v6.0
st.markdown(f"""
<div class="hero-welcome">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0;">¡Hola, {st.session_state.get('username', 'Aspirante')}! 👋</h1>
            <p style="font-size: 1.1rem; color: var(--text-muted); margin-top: 5px;">Bienvenido a tu Centro de Control de Preparación para la DIAN.</p>
        </div>
        <div style="text-align: right;">
            <span style="font-size: 2.5rem;">{rank["icon"] if rank else '🎓'}</span>
            <div style="font-weight: 800; color: var(--dian-red);">{rank["name"] if rank else 'Estudiante'}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Metrics Grid section
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    metric_card(
        label="🔥 Racha Actual",
        value=str(stats_s.current_streak if stats_s else 0),
        sublabel="Días seguidos"
    )
with m_col2:
    metric_card(
        label="🏆 Puntaje Total",
        value=str(stats_s.total_points if stats_s else 0),
        sublabel="Puntos de Maestría"
    )
with m_col3:
    # Calculate global success rate if possible
    # (Assuming we can fetch total hits/misses from stats or simple query)
    metric_card(
        label="🎯 Precisión",
        value="92%", # Placeholder o query rápido
        sublabel="Aciertos globales"
    )

st.markdown("<br>", unsafe_allow_html=True)

# Main Grid: Quick Actions vs OPEC Status
col_left, col_right = st.columns([0.6, 0.4])

with col_left:
    st.markdown("### ⚡ Acciones Rápidas")
    
    # Grid for action buttons
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        st.markdown(f"""
        <a href="/Nuevo_Simulacro" target="_self" class="quick-action-btn">
            <span style="font-size: 1.5rem;">🚀</span>
            <span>Nuevo Simulacro</span>
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <a href="/Banco_Preguntas" target="_self" class="quick-action-btn" style="margin-top: 15px;">
            <span style="font-size: 1.5rem;">📚</span>
            <span>Explorar Banco</span>
        </a>
        """, unsafe_allow_html=True)

    with q_col2:
        st.markdown(f"""
        <a href="/Resultados" target="_self" class="quick-action-btn">
            <span style="font-size: 1.5rem;">📈</span>
            <span>Ver Progreso</span>
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <a href="/Generador_IA" target="_self" class="quick-action-btn" style="margin-top: 15px;">
            <span style="font-size: 1.5rem;">🤖</span>
            <span>Generador IA</span>
        </a>
        """, unsafe_allow_html=True)

with col_right:
    st.markdown("### 📋 Meta Activa")
    # Fetch active OPEC info
    db = SessionLocal()
    u_opec = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
    db.close()
    
    if u_opec:
        st.markdown(f"""
        <div class="dian-card" style="padding: 1.5rem; border-left: 5px solid var(--dian-red);">
            <div style="font-weight: 800; color: var(--dian-red); font-size: 0.8rem; text-transform: uppercase;">{u_opec.opec_number}</div>
            <div style="font-size: 1.2rem; font-weight: 700; margin: 5px 0;">{u_opec.job_title}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">{u_opec.level}</div>
            <hr style="opacity: 0.1; margin: 15px 0;">
            <div style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; margin-bottom: 5px;">Maestría del Cargo</div>
            <div style="background: rgba(0,0,0,0.05); height: 10px; border-radius: 5px; overflow: hidden;">
                <div style="background: linear-gradient(90deg, #E60000, #FFD700); width: 65%; height: 100%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("No tienes una OPEC activa seleccionada.")
        if st.button("Configurar OPEC Ahora", use_container_width=True):
            st.switch_page("pages/3_Configuración_OPEC.py")

# Initialize session state for generic use
if "user_session" not in st.session_state:
    st.session_state["user_session"] = str(os.urandom(8))
