import streamlit as st
import sys
import os

# Add root to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mikey v7.2: Eliminamos imports ORM del top-level para evitar crasheos por desincronización
# from db.session import SessionLocal
# from db.models import User, UserOPEC...
from ui_utils import load_css, render_header, metric_card, render_custom_sidebar
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

# Debug Google Auth
if st.query_params.get("debug") == "1":
    try:
        st.write("Google User Info:", st.user)
    except:
        st.write("st.user no disponible")

if not AuthManager.check_auth():
    # mikey v7.17: Si estamos en la pantalla de login, permitir re-entrada limpia
    if st.query_params.get("logout") == "1":
        if st.button("🔄 Volver a Iniciar Sesión", use_container_width=True, type="primary"):
            st.query_params.clear()
            st.rerun()
        st.info("Has cerrado sesión correctamente. mikey.")
        st.stop()

    load_css()
    render_header(title="Acceso al Simulador", subtitle="Identifícate para continuar tu preparación")
    
    col_l1, col_l2 = st.columns([1, 1])
    
    with col_l1:
        st.subheader("🔑 Iniciar Sesión")
        with st.form("login_form"):
            user_in = st.text_input("Usuario")
            pass_in = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)
            
            if btn_login:
                try:
                    if AuthManager.login(user_in, pass_in):
                        st.success("¡Bienvenido!")
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

        st.markdown("---")
        # Integración NATIVA Google OAuth mikey v3.0 (Streamlit 1.42+)
        try:
            # Verificar si existen los secretos antes de intentar st.login()
            has_google = "auth" in st.secrets and "google" in st.secrets.auth
            
            if has_google:
                st.markdown("<p style='text-align: center; color: gray;'>O usa tu cuenta corporativa:</p>", unsafe_allow_html=True)
                if st.button("🚀 Continuar con Google", use_container_width=True, type="secondary"):
                    st.login("google")
            else:
                with st.expander("ℹ️ ¿Cómo activar el login con Google?"):
                    st.info("Para activar esta función, debes configurar los 'Secrets' en Streamlit Cloud.")
                    st.code("[auth]\nredirect_uri = \"...\"\ncookie_secret = \"...\"\n\n[auth.google]\nclient_id = \"...\"\nclient_secret = \"...\"", language="toml")
        except Exception as e:
            st.error(f"Error en Google Login Nativo: {e}")

    with col_l2:
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
                    from sqlalchemy import text
                    from db.session import engine
                    with engine.connect() as check_conn:
                        sql_up = text("SELECT id FROM users WHERE username = :u")
                        if check_conn.execute(sql_up, {"u": new_user}).first():
                            st.error("El usuario ya existe")
                        else:
                            try:
                                hashed = AuthManager.hash_password(new_pass)
                                with engine.begin() as ins_conn:
                                    sql_ins = text("INSERT INTO users (username, password_hash) VALUES (:u, :p)")
                                    ins_conn.execute(sql_ins, {"u": new_user, "p": hashed})
                                st.success("Cuenta creada. ¡Ya puedes entrar!")
                            except Exception as e:
                                st.error(f"Error al registrar: {e}")
    st.stop() # Stop execution here if not logged in

# --- v2.0 NEW: Sidebar Gamification Info ---
stats_s, rank = render_custom_sidebar()
u_id = st.session_state.get("user_id")


# Inject Global CSS
load_css()

try:
    from app.components.NewsTicker import render_news_ticker
except ImportError:
    from components.NewsTicker import render_news_ticker

# Render Custom Header
render_header()

# --- Paywall Global Mikey v4.0 ---
if st.session_state.get("show_paywall"):
    from ui_utils import render_paywall_card
    if st.button("⬅️ Cerrar e Ir Atrás", use_container_width=False):
        st.session_state["show_paywall"] = False
    render_paywall_card("Acceso Pro Ilimitado")
    st.stop()

# v6.3: Regulatory Flash Updates
render_news_ticker()

# Introduction / Hero Dashboard v6.0
try:
    is_pro_user = AuthManager.is_pro()
except:
    is_pro_user = False

pro_tag = '<div style="background: #FFD700; color: black; padding: 2px 8px; border-radius: 4px; font-size: 0.6rem; font-weight: 900; margin-top: 5px;">✨ PRO</div>' if is_pro_user else ""

st.markdown(f"""
<div class="hero-welcome">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0;">¡Hola, {st.session_state.get('username') or 'Aspirante'}! 👋</h1>
            <p style="font-size: 1.1rem; color: var(--text-muted); margin-top: 5px;">Bienvenido a tu Centro de Control de Preparación para la DIAN.</p>
        </div>
        <div style="text-align: right;">
            <span style="font-size: 2.5rem;">{rank["icon"] if rank else '🎓'}</span>
            <div style="font-weight: 800; color: var(--dian-red);">{rank["name"] if rank else 'Estudiante'}</div>
            {pro_tag}
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
        st.page_link("pages/1_Nuevo_Simulacro.py", label="Nuevo Simulacro", icon="🚀", use_container_width=True)
        st.page_link("pages/5_Banco_Preguntas.py", label="Explorar Banco", icon="📚", use_container_width=True)

    with q_col2:
        st.page_link("pages/3_Resultados.py", label="Ver Progreso", icon="📈", use_container_width=True)
        st.page_link("pages/4_Generador_IA.py", label="Generador IA", icon="🤖", use_container_width=True)

with col_right:
    st.markdown("### 📋 Meta Activa")
    # Fetch active OPEC info - Mikey v5.0 Safety
    u_opec = None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            sql = text("SELECT opec_number, job_title, level FROM user_opec WHERE user_id = :uid AND is_active = True LIMIT 1")
            u_opec = conn.execute(sql, {"uid": u_id}).first()
    except Exception as opec_err:
        print(f"⚠️ [APP] OPEC Fetch Error: {opec_err}")
    
    if u_opec:
        st.markdown(f"""
        <div class="dian-card" style="padding: 1.5rem; border-left: 5px solid var(--dian-red);">
            <div style="font-weight: 800; color: var(--dian-red); font-size: 0.8rem; text-transform: uppercase;">{u_opec[0]}</div>
            <div style="font-size: 1.2rem; font-weight: 700; margin: 5px 0;">{u_opec[1]}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">{u_opec[2]}</div>
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
            st.switch_page("pages/7_Configuracion_OPEC.py")

# Initialize session state for generic use
if "user_session" not in st.session_state:
    st.session_state["user_session"] = str(os.urandom(8))
