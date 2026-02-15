import streamlit as st
import os

def load_css():
    """Inyecta el CSS personalizado en la aplicación."""
    # Build absolute path to styles.css assuming it's in the same directory as this file (app/)
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    
    if os.path.exists(css_path):
        with open(css_path, "r", encoding='utf-8') as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        # Fallback if file not found (shouldn't happen in dev)
        st.warning(f"No se encontró el archivo de estilos en: {css_path}")

def render_header(title: str = None, subtitle: str = None):
    """Renderiza el encabezado estándar de DIAN Sim."""
    
    col_logo, col_text = st.columns([0.4, 0.6])
    
    with col_logo:
        # Relativizado para el despliegue
        # El logo debe estar en app/assets/logo.png
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        try:
            if os.path.exists(logo_path):
                # V50.1 Mikey: Clickable Logo (Base64)
                import base64
                with open(logo_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                
                # Use HTML to make it clickable (Main Page Redirect)
                st.markdown(
                    f"""
                    <a href="/" target="_self">
                        <img src="data:image/png;base64,{encoded_string}" width="280" style="margin-bottom: 10px; transition: transform 0.3s ease;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    </a>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<h1 style='color: var(--dian-red); font-size: 2.2rem; margin:0;'>DIAN Sim</h1>", unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f"🇨🇴 **DIAN Sim** ({e})")
            
    with col_text:
        if title:
            # Inline flex for title + status badge
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0;">
                <h2 style='margin: 0;'>{title}</h2>
                {_get_conn_badge()}
            </div>
            """, unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<p style='color: var(--dian-text-muted); font-size: 0.85rem; margin-top: -5px;'>{subtitle}</p>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.1;'>", unsafe_allow_html=True)

def _get_conn_badge():
    """Retorna un badge HTML según el tipo de conexión activa. Mikey"""
    try:
        from db.session import DATABASE_URL
        if not DATABASE_URL:
            return ""
        is_cloud = "supabase" in DATABASE_URL.lower() or "postgres" in DATABASE_URL.lower()
        
        if is_cloud:
            return '<span style="background: rgba(0, 200, 100, 0.2); color: #00ff88; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; border: 1px solid #00ff88; font-weight: bold; text-transform: uppercase;">🌐 Nube (Sync)</span>'
        else:
            return '<span style="background: rgba(255, 150, 0, 0.2); color: #ff9900; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; border: 1px solid #ff9900; font-weight: bold; text-transform: uppercase;">🏠 Local (Offline)</span>'
    except Exception:
        return ""

def card_container(key=None):
    """Retorna un contenedor estilo tarjeta."""
    return st.container(border=True) # Streamlit's native container with border maps well to our styling if customized, 
                                     # or we can use markdown divs. Let's stick to native for interaction, 
                                     # but inject a wrapper class if possible. 
                                     # Streamlit doesn't easily allow adding classes to containers. 
                                     # Hybrid approach: Use native for layout, customize global border/bg via CSS.

def metric_card(label: str, value: str, sublabel: str = ""):
    """Renderiza una tarjeta de métrica personalizada."""
    st.markdown(f"""
    <div class="dian-card" style="text-align: center; padding: 1.5rem;">
        <div class="dian-card-header" style="justify-content: center;">{label}</div>
        <div style="font-size: 2.2rem; font-weight: 800; color: var(--text-main); margin: 10px 0;">{value}</div>
        <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">{sublabel}</div>
    </div>
    """, unsafe_allow_html=True)

def render_custom_sidebar():
    """Renderiza el sidebar categorizado con gamificación v6.2. Mikey"""
    from db.session import SessionLocal
    from db.models import UserStats
    from core.rank_system import get_rank_info
    from core.auth import AuthManager
    
    db_s = SessionLocal()
    u_id = st.session_state.get("user_id")
    stats_s = None
    rank = {"name": "Aspirante", "icon": "🎓", "color": "#475569", "threshold": 0}
    next_rank = None
    pct = 0
    
    try:
        if u_id:
            stats_s = db_s.query(UserStats).filter_by(user_id=u_id).first()
            user_m = db_s.query(User).filter_by(id=u_id).first()
            is_pro = AuthManager.is_pro()
        
        if not stats_s and u_id:
            stats_s = UserStats(user_id=u_id, current_streak=0, max_streak=0, total_points=0)
            db_s.add(stats_s)
            db_s.commit()
            db_s.refresh(stats_s)
            
        if stats_s:
            rank, next_rank = get_rank_info(stats_s.total_points)
            if next_rank:
                total_needed = next_rank["threshold"] - rank["threshold"]
                current_progress = stats_s.total_points - rank["threshold"]
                pct = min(100, int((current_progress / total_needed) * 100))
            else:
                pct = 100
            
            # Badge de Pro mikey v4.0
            pro_badge = '<div style="background: linear-gradient(90deg, #FFD700, #FFA500); color: black; padding: 2px 8px; border-radius: 4px; font-size: 0.6rem; font-weight: 900; margin-top: 5px; display: inline-block;">✨ USUARIO PRO</div>' if is_pro else ""
                
            st.sidebar.markdown(f"""
            <div class="dian-card" style='padding: 20px; text-align: center; margin-bottom: 5px; border-top: 3px solid {rank["color"]};'>
                <div style='font-size: 0.7rem; color: var(--text-muted); font-weight: 800; text-transform: uppercase; letter-spacing: 2px;'>Rango Actual</div>
                <div style='font-size: 2.5rem; margin: 5px 0;'>{rank["icon"]}</div>
                <div style='font-size: 1.1rem; font-weight: 800; color: {rank["color"]}; margin-bottom: 5px;'>{rank["name"]}</div>
                {pro_badge}
                <div style='background: rgba(0,0,0,0.05); height: 8px; border-radius: 4px; margin: 10px 0; overflow: hidden;'>
                    <div style='background: {rank["color"]}; width: {pct}%; height: 100%; transition: width 0.5s ease;'></div>
                </div>
                <div style='font-size: 0.7rem; color: var(--text-muted);'>
                    {stats_s.total_points} / {next_rank["threshold"] if next_rank else "MAX"} PTS
                </div>
            </div>
            """, unsafe_allow_html=True)

        if not is_pro:
            if st.sidebar.button("🚀 ¡Pasar a PRO!", use_container_width=True, type="primary"):
                st.session_state["show_paywall"] = True
                st.rerun()

        st.sidebar.markdown('<div class="sidebar-category">🚀 Mi Entrenamiento</div>', unsafe_allow_html=True)
        st.sidebar.markdown('<div class="sidebar-category">🛠️ Herramientas AI</div>', unsafe_allow_html=True)
        st.sidebar.markdown('<div class="sidebar-category">⚙️ Configuración</div>', unsafe_allow_html=True)
        
        st.sidebar.button("🚪 Cerrar Sesión", on_click=AuthManager.logout, use_container_width=True, key="sidebar_logout_btn")
        
    except Exception as e:
        st.sidebar.error(f"⚠️ Sidebar Error: {e}")
    finally:
        db_s.close()
    
    return stats_s, rank
def get_db_info():
    """Retorna información del estado de la base de datos. Mikey"""
    from db.session import SessionLocal, DATABASE_URL
    from db.models import Question
    try:
        db = SessionLocal()
        count = db.query(Question).count()
        db.close()
        db_type = "Cloud (Supabase)" if "postgres" in DATABASE_URL.lower() else "Local (SQLite)"
        return count, db_type
    except Exception as e:
        return 0, f"Error: {e}"

def render_favorite_button(question_id: str, user_id: int):
    """Renderiza un botón para marcar/desmarcar favoritas. Mikey"""
    from db.session import SessionLocal
    from db.models import QuestionPerformance
    
    if not user_id:
        return

    db = SessionLocal()
    try:
        perf = db.query(QuestionPerformance).filter_by(user_id=user_id, question_id=question_id).first()
        is_fav = perf.is_favorite if perf else False
        
        label = "⭐ Favorita" if is_fav else "☆ Favorita"
        # Usamos un estilo de botón de streamlit transparente si fuera posible, 
        # pero para mantener el diseño premium usaremos el estándar con un color distinto si es fav.
        
        if st.button(label, key=f"fav_{question_id}", use_container_width=False):
            if not perf:
                perf = QuestionPerformance(user_id=user_id, question_id=question_id, hits=0, misses=0, is_favorite=True)
                db.add(perf)
            else:
                perf.is_favorite = not is_fav
            
            db.commit()
            st.rerun()
            
    except Exception as e:
        st.error(f"Error al guardar favorito: {e}")
    finally:
        db.close()

def render_paywall_card(feature_name: str = "esta función"):
    """Muestra un modal/banner invitando a suscribirse a PRO. mikey v4.0"""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 30px; border-radius: 16px; border: 1px solid rgba(255, 215, 0, 0.3); text-align: center; margin: 20px 0;">
        <h2 style="color: #FFD700; margin-bottom: 10px;">✨ Desbloquea el Acceso PRO</h2>
        <p style="color: #cbd5e1; font-size: 1.1rem;">Lo sentimos, <b>{feature_name}</b> es exclusivo para miembros PRO.</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; text-align: left; margin: 25px auto; max-width: 400px;">
            <div style="color: #94a3b8; font-size: 0.9rem;">✅ IA Ilimitada</div>
            <div style="color: #94a3b8; font-size: 0.9rem;">✅ Banco de Errores</div>
            <div style="color: #94a3b8; font-size: 0.9rem;">✅ Simulacros 100 Qs</div>
            <div style="color: #94a3b8; font-size: 0.9rem;">✅ Estadísticas Avanzadas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    from services.stripe_service import StripeService
    user_email = st.session_state.get("user_email")
    user_id = st.session_state.get("user_id")
    
    if st.button("🌟 SUSCRIBIRME AHORA (Obtener Acceso Total)", use_container_width=True, type="primary"):
        checkout_url = StripeService.create_checkout_session(user_email, user_id)
        if checkout_url:
            st.markdown(f'<meta http-equiv="refresh" content="0; url={checkout_url}">', unsafe_allow_html=True)
            st.info("Redirigiendo a Stripe seguro...")
        else:
            st.error("Error al conectar con la pasarela de pago. Intenta más tarde.")

def check_feature_access(feature: str, is_pro_required: bool = True):
    """Helper para verificar acceso y mostrar el paywall si es necesario. mikey"""
    from core.auth import AuthManager
    if is_pro_required and not AuthManager.is_pro():
        render_paywall_card(feature)
        return False
    return True
