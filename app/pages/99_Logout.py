import streamlit as st
from core.auth import AuthManager

# pass # Removed st.set_page_config

st.info("Cerrando sesión de forma segura...")
AuthManager.logout()
st.stop()
