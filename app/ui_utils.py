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
                st.image(logo_path, width=380)
            else:
                st.markdown("<h1 style='color: var(--dian-red); font-size: 3rem; margin:0;'>DIAN Sim</h1>", unsafe_allow_html=True)
        except Exception:
            st.markdown("🇨🇴 **DIAN Sim**")
            
    with col_text:
        if title:
            st.markdown(f"<h2 style='margin-bottom: 0;'>{title}</h2>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<p style='color: var(--dian-text-muted); font-size: 0.9rem;'>{subtitle}</p>", unsafe_allow_html=True)
    
    st.divider()

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
