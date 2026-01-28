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
                # Using st.image directly for reliability
                st.image(logo_path, width=280) # Sized down from 380
            else:
                st.markdown("<h1 style='color: var(--dian-red); font-size: 2.2rem; margin:0;'>DIAN Sim</h1>", unsafe_allow_html=True)
        except Exception:
            st.markdown("🇨🇴 **DIAN Sim**")
            
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
    from db.session import DATABASE_URL
    is_cloud = "supabase" in DATABASE_URL.lower() or "postgres" in DATABASE_URL.lower()
    
    if is_cloud:
        return '<span style="background: rgba(0, 200, 100, 0.2); color: #00ff88; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; border: 1px solid #00ff88; font-weight: bold; text-transform: uppercase;">🌐 Nube (Sync)</span>'
    else:
        return '<span style="background: rgba(255, 150, 0, 0.2); color: #ff9900; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; border: 1px solid #ff9900; font-weight: bold; text-transform: uppercase;">🏠 Local (Offline)</span>'

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
