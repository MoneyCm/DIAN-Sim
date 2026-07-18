import streamlit as st
import time

# pass # Removed st.set_page_config

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
st.query_params["logout"] = "1"
st.rerun()
