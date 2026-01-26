import streamlit as st
import sys
import os

# Add root to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import SessionLocal
from db.models import UserStats, User
from ui_utils import load_css, render_header
from core.auth import AuthManager

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
try:
    u_id = st.session_state.get("user_id")
    stats_s = db_s.query(UserStats).filter_by(user_id=u_id).first()
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
<div class="dian-card" style='padding: 20px; text-align: center; margin-bottom: 10px; border-top: 3px solid {rank["color"]};'>
    <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 800; text-transform: uppercase; letter-spacing: 2px;'>Rango Actual</div>
    <div style='font-size: 2.5rem; margin: 5px 0;'>{rank["icon"]}</div>
    <div style='font-size: 1.1rem; font-weight: 800; color: {rank["color"]}; margin-bottom: 5px;'>{rank["name"]}</div>
    <div style='background: rgba(0,0,0,0.05); height: 8px; border-radius: 4px; margin: 10px 0; overflow: hidden;'>
        <div style='background: {rank["color"]}; width: {pct}%; height: 100%; transition: width 0.5s ease;'></div>
    </div>
    <div style='font-size: 0.7rem; color: var(--text-muted);'>
        {stats_s.total_points} / {next_rank["threshold"] if next_rank else "MAX"} PTS
    </div>
    <hr style="margin: 15px 0; opacity: 0.1;">
    <div style="display: flex; justify-content: space-around;">
        <div style="text-align: center;">
            <div style="font-size: 1.2rem;">🔥</div>
            <div style="font-size: 0.8rem; font-weight: 700;">{stats_s.current_streak}</div>
            <div style="font-size: 0.6rem; color: var(--text-muted);">RACHA</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 1.2rem;">🏆</div>
            <div style="font-size: 0.8rem; font-weight: 700;">{stats_s.max_streak}</div>
            <div style="font-size: 0.6rem; color: var(--text-muted);">MÁXIMA</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
    st.sidebar.button("🚪 Cerrar Sesión", on_click=AuthManager.logout, use_container_width=True)
except Exception as e:
    st.sidebar.error(f"⚠️ Error: {e}")
db_s.close()


# Inject Global CSS
load_css()

# Render Custom Header
render_header()

# Introduction Card
st.markdown('<div class="dian-card">', unsafe_allow_html=True)
st.markdown('<div class="dian-card-header">Bienvenido al Ecosistema de Estudio</div>', unsafe_allow_html=True)
st.markdown('<h1 style="margin-top: 0;">Impulsa tu Carrera en la DIAN</h1>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 1.15rem; color: var(--text-muted); line-height: 1.6;">Prepárate con la herramienta de simulación más avanzada, diseñada para adaptarse a tu ritmo y fortalecer tus competencias legales.</p>', unsafe_allow_html=True)

# Grid of features
st.markdown("""
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 30px; margin-top: 50px; margin-bottom: 20px;">
    <div style="background: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.8); border-radius: 20px; padding: 25px; transition: all 0.3s ease;">
        <div style="font-size: 2.5rem; margin-bottom: 15px;">🧠</div>
        <h4 style="margin-bottom: 10px;">Entrenamiento Adaptativo</h4>
        <p style="font-size: 0.95rem; color: var(--text-muted); line-height: 1.5;">Algoritmos inteligentes que priorizan tus áreas de mejora para un estudio guiado.</p>
    </div>
    <div style="background: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.8); border-radius: 20px; padding: 25px; transition: all 0.3s ease;">
        <div style="font-size: 2.5rem; margin-bottom: 15px;">🤖</div>
        <h4 style="margin-bottom: 10px;">Tutoría IA Socrática</h4>
        <p style="font-size: 0.95rem; color: var(--text-muted); line-height: 1.5;">Domina la lógica legal detrás de cada situación con nuestro experto virtual.</p>
    </div>
    <div style="background: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.8); border-radius: 20px; padding: 25px; transition: all 0.3s ease;">
        <div style="font-size: 2.5rem; margin-bottom: 15px;">📊</div>
        <h4 style="margin-bottom: 10px;">Analítica Visual</h4>
        <p style="font-size: 0.95rem; color: var(--text-muted); line-height: 1.5;">Monitorea tu crecimiento con radares de competencia y métricas de racha.</p>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; margin-top: 40px; color: var(--text-muted);">
    Selecciona <b>"Nuevo Simulacro"</b> en el menú lateral para comenzar tu sesión.
</div>
""", unsafe_allow_html=True)

# Initialize session state for generic use
if "user_session" not in st.session_state:
    st.session_state["user_session"] = str(os.urandom(8))
