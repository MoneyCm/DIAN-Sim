import streamlit as st
import sys
import os

# Add root to python path to import modules
APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))
for import_path in (APP_DIR, PROJECT_ROOT):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

# Mikey v7.2: Eliminamos imports ORM del top-level para evitar crasheos por desincronización
# from db.session import SessionLocal
# from db.models import User, UserOPEC...
try:
    from ui_utils import load_css, render_header, metric_card, render_custom_sidebar
except ImportError:
    from app.ui_utils import load_css, render_header, metric_card, render_custom_sidebar
from core.auth import AuthManager
from core.access_control import is_admin
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

# --- CRITICAL AUTH FIX v8.0 ---
# Force Logout Logic moved to top-level app.py to prevent caching issues
# and handle native Google Session persistence.
if "logout" in st.query_params:
    # 1. Clear Local Session
    if st.session_state.get("logged_in"):
        st.session_state.clear()
    
    # 2. Force Native Google Logout (The missing piece)
    try:
        if st.user.is_logged_in:
             st.logout() # This triggers a rerun automatically
    except:
        pass

    # 3. Show Logout Screen
    if st.button("🔄 Volver a Iniciar Sesión", use_container_width=True, type="primary"):
        st.query_params.clear()
        st.rerun()
    st.info("Has cerrado sesión correctamente. (v8.0)")
    st.stop()

def login_view():
    # mikey v7.17: Legacy block kept for fallback, but logic above should catch it first.
    pass

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
                        st.rerun() # Refresh app to switch st.navigation mode
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
            # En entorno local sin secrets.toml dict explota con FileNotFoundError
            has_google = False
            try:
                if "auth" in st.secrets and "google" in st.secrets.auth:
                    has_google = True
            except FileNotFoundError:
                pass # Local sin secretos, ignorar sin romper
            except Exception:
                pass # Otros errores de lectura
            
            if has_google:
                st.markdown("<p style='text-align: center; color: gray;'>O usa tu cuenta corporativa:</p>", unsafe_allow_html=True)
                if st.button("🚀 Continuar con Google", use_container_width=True, type="secondary"):
                    # mikey cleanup: Allow re-login by clearing the manual logout flag
                    if "logout_manual_flag" in st.session_state:
                        del st.session_state["logout_manual_flag"]
                    st.login("google")
            else:
                with st.expander("ℹ️ ¿Cómo activar el login con Google?"):
                    st.info("Para activar esta función, debes configurar los 'Secrets' en Streamlit Cloud.")
                    st.code("[auth]\nredirect_uri = \"...\"\ncookie_secret = \"...\"\n\n[auth.google]\nclient_id = \"...\"\nclient_secret = \"...\"", language="toml")
        except Exception as e:
            # Evitamos colapsar la app entera si falla esta sección visual
            st.error(f"Aviso Login Nativo: {e}")

    with col_l2:
        st.subheader("📝 Registrarse")
        st.info("¿Aún no tienes cuenta? Crea una para guardar tus 5 cargos (OPECs).")
        with st.form("register_form"):
            new_user = st.text_input("Nuevo Usuario")
            new_pass = st.text_input("Contraseña", type="password")
            confirm_pass = st.text_input("Confirmar Contraseña", type="password")
            btn_reg = st.form_submit_button("Crear Cuenta", use_container_width=True)
            
            if btn_reg:
                clean_user = new_user.strip()
                if not clean_user or not new_pass:
                    st.error("Completa todos los campos")
                elif len(new_pass) < 8:
                    st.error("La contraseña debe tener al menos 8 caracteres")
                elif new_pass != confirm_pass:
                    st.error("Las contraseñas no coinciden")
                else:
                    from sqlalchemy import text
                    from db.session import engine
                    with engine.connect() as check_conn:
                        sql_up = text("SELECT id FROM users WHERE username = :u")
                        if check_conn.execute(sql_up, {"u": clean_user}).first():
                            st.error("El usuario ya existe")
                        else:
                            try:
                                hashed = AuthManager.hash_password(new_pass)
                                with engine.begin() as ins_conn:
                                    sql_ins = text(
                                        "INSERT INTO users (username, password_hash, role) "
                                        "VALUES (:u, :p, 'user')"
                                    )
                                    ins_conn.execute(sql_ins, {"u": clean_user, "p": hashed})
                                st.success("Cuenta creada. ¡Ya puedes entrar!")
                            except Exception as e:
                                st.error(f"Error al registrar: {e}")

# --- NAVEGACIÓN CENTRALIZADA (st.navigation) v9.0 ---
# Definición de páginas (st.Page deshabilita el menú automático caótico)

# Grupo: Mi Cuenta
p_dashboard = st.Page("pages/6_Dashboard.py", title="Dashboard", icon="📊", default=True)
p_perfil = st.Page("pages/7_Mi_Perfil.py", title="Mi Perfil", icon="👤")
p_config = st.Page("pages/7_Configuracion_OPEC.py", title="Configuración OPEC", icon="⚙️")
p_study_plan = st.Page("pages/11_Plan_Estudio.py", title="Plan de estudio", icon="🗓️")
p_study_map = st.Page("pages/12_Mapa_Estudio.py", title="Mapa de estudio", icon="🗺️")
p_adaptive_tutor = st.Page("pages/13_Tutor_Adaptativo.py", title="Tutor adaptativo", icon="🧭")
p_logout = st.Page("pages/99_Logout.py", title="Cerrar Sesión", icon="🚪")

# Grupo: Práctica
p_simulacro = st.Page("pages/1_Nuevo_Simulacro.py", title="Práctica personalizada", icon="📚")
p_ejecucion = st.Page("pages/2_Ejecucion.py", title="Simulacro en curso", icon="▶️")
p_sim_real = st.Page("pages/Simulacro_Real.py", title="Simulacro tipo examen", icon="⏱️")
p_repaso = st.Page("pages/10_Repaso_Especial.py", title="Repasos de hoy", icon="🧠")
p_resultados = st.Page("pages/3_Resultados.py", title="Resultados y Progreso", icon="📈")

# Grupo: Recursos
p_ia = st.Page("pages/4_Generador_IA.py", title="Generador IA", icon="🤖")
p_banco = st.Page("pages/5_Banco_Preguntas.py", title="Banco de Preguntas", icon="📚")
p_etica = st.Page("pages/9_Etica_Integridad.py", title="Ética e Integridad", icon="⚖️")

# Grupo: Administración (Sistemas)
p_admin = st.Page("pages/8_Panel_Admin.py", title="Panel de Control", icon="🛡️")

# Agrupar menú
pages = {
    "Mi Cuenta": [p_dashboard, p_perfil, p_config, p_study_plan, p_study_map, p_logout],
    "Práctica DIAN": [p_adaptive_tutor, p_simulacro, p_ejecucion, p_sim_real, p_repaso, p_resultados],
    "Herramientas y Recursos": [p_banco, p_etica]
}

# Determinar Navegación Activa (Condicional)
if not AuthManager.check_auth():
    # Modo no logueado: Forzar el router de 1 sola página (Login)
    p_main_login = st.Page(login_view, title="Iniciar Sesión", icon="🔒")
    pg = st.navigation([p_main_login])
else:
    # Modo logueado: Montar la app entera y sus funciones
    # Inject Global CSS and render visual wrappers before page execution
    load_css()
    # Restaurar la info de Gamificación en la barra lateral del usuario v9.1
    try:
        render_custom_sidebar()
    except Exception as e:
        pass
        
    if is_admin():
        pages["Sistemas (Admin)"] = [p_admin, p_ia]
    if st.session_state.get("opec_onboarding"):
        pg = st.navigation({"Primeros pasos": [p_config]})
    else:
        pg = st.navigation(pages)

# Ejecutar la página seleccionada por el router
pg.run()
