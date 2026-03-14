import streamlit as st
import time

# st.set_page_config(page_title="Cerrando Sesión...", layout="centered")

# Limpieza Total
for key in list(st.session_state.keys()):
    del st.session_state[key]

# Bandera Manual
st.session_state["logout_manual_flag"] = True

# Mensaje Visual
st.info("Cerrando sesión de forma segura...")
progress = st.progress(0)
for i in range(100):
    time.sleep(0.01)
    progress.progress(i + 1)

# Redirección Final
st.switch_page("app.py")
