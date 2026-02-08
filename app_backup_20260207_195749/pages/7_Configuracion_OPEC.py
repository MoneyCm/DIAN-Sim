import streamlit as st
import os, sys, json

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import UserOPEC
from ui_utils import load_css, render_header, render_custom_sidebar

from core.auth import AuthManager

st.set_page_config(page_title="Configuración OPEC | DIAN Sim", page_icon="🎯", layout="wide")

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión en la página principal.")
    st.stop()

load_css()
render_custom_sidebar()
render_header(title="Mi Meta: OPEC", subtitle="Configura tu cargo y enfoca tu preparación")

def get_active_opec():
    db = SessionLocal()
    u_id = st.session_state.get("user_id")
    opec = db.query(UserOPEC).filter_by(user_id=u_id, is_active=True).first()
    db.close()
    return opec

active_opec = get_active_opec()
u_id = st.session_state.get("user_id")

st.markdown("""
<div class="dian-card">
    Configura aquí el <b>Número OPEC</b> de la vacante a la que aspiras. Esto permitirá que la IA genere preguntas 
    específicamente para las funciones y requisitos de tu cargo.
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Datos del Empleo")
    with st.form("opec_form"):
        opec_number = st.text_input("Número OPEC", value=active_opec.opec_number if active_opec else "", placeholder="Ej: 198273")
        job_title = st.text_input("Nombre del Cargo", value=active_opec.job_title if active_opec else "", placeholder="Ej: Gestor II - Auditoría")
        level = st.selectbox("Nivel Jerárquico", ["Profesional", "Técnico", "Asistencial"], index=0 if not active_opec else ["Profesional", "Técnico", "Asistencial"].index(active_opec.level))
        
        purpose = st.text_area("Propósito del Empleo", value=active_opec.purpose if active_opec else "", height=100)
        
        raw_functions = ""
        if active_opec and active_opec.functions:
            if isinstance(active_opec.functions, list):
                raw_functions = "\n".join(active_opec.functions)
            else:
                raw_functions = str(active_opec.functions)
                
        functions_text = st.text_area("Funciones (una por línea)", value=raw_functions, height=200, help="Copia y pega el manual de funciones aquí.")
        
        requirements = st.text_area("Requisitos de Estudio y Experiencia", value=active_opec.requirements if active_opec else "", height=100)
        
        submit = st.form_submit_button("🎯 Guardar y Enfocar Simulador", type="primary", use_container_width=True)
        
        if submit:
            if not opec_number or not job_title:
                st.error("Por favor completa el Número OPEC y el Nombre del Cargo.")
            else:
                db = SessionLocal()
                try:
                    # Deactivate others for THIS user
                    db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
                    
                    # Process functions into JSON list
                    func_list = [f.strip() for f in functions_text.split("\n") if f.strip()]
                    
                    # Check if this OPEC already exists FOR THIS USER
                    existing = db.query(UserOPEC).filter_by(user_id=u_id, opec_number=opec_number).first()
                    if existing:
                        existing.job_title = job_title
                        existing.level = level
                        existing.purpose = purpose
                        existing.functions = func_list
                        existing.requirements = requirements
                        existing.is_active = True
                    else:
                        new_opec = UserOPEC(
                            user_id=u_id,
                            opec_number=opec_number,
                            job_title=job_title,
                            level=level,
                            purpose=purpose,
                            functions=func_list,
                            requirements=requirements,
                            is_active=True
                        )
                        db.add(new_opec)
                    
                    db.commit()
                    st.success(f"¡Configuración de OPEC {opec_number} guardada!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"Error al guardar: {e}")
                finally:
                    db.close()

with col2:
    st.subheader("🎯 Resumen y Gestión Multi-Cargo")
    
    db_list = SessionLocal()
    all_user_opecs = db_list.query(UserOPEC).filter_by(user_id=u_id).order_by(UserOPEC.updated_at.desc()).all()
    db_list.close()
    
    if all_user_opecs:
        st.write(f"Tienes **{len(all_user_opecs)}/5** cargos configurados.")
        
        for o in all_user_opecs:
            with st.expander(f"{'⭐' if o.is_active else '📁'} {o.job_title} (OPEC {o.opec_number})", expanded=o.is_active):
                st.write(f"**Nivel:** {o.level}")
                st.write(f"**Propósito:** {o.purpose}")
                
                col_act, col_del = st.columns(2)
                with col_act:
                    if not o.is_active:
                        if st.button("Activar para Estudio", key=f"act_{o.id}"):
                            db = SessionLocal()
                            db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
                            db.query(UserOPEC).filter_by(id=o.id).update({UserOPEC.is_active: True})
                            db.commit()
                            db.close()
                            st.success(f"Ahora estás enfocado en {o.job_title}")
                            st.rerun()
                with col_del:
                    if st.button("Eliminar Cargo", key=f"del_{o.id}", type="secondary"):
                        db = SessionLocal()
                        db.query(UserOPEC).filter_by(id=o.id).delete()
                        db.commit()
                        db.close()
                        st.rerun()
    else:
        st.warning("No tienes una OPEC configurada todavía. El simulador usará temas generales hasta que definas tu meta.")
        st.image("https://img.icons8.com/color/96/000000/target.png")

    if len(all_user_opecs) >= 5:
        st.error("⚠️ Has alcanzado el límite de 5 cargos. Elimina uno para agregar uno nuevo.")
    
st.divider()
st.caption("🔒 Los datos de tu OPEC se guardan de forma segura en tu base de datos para que la IA los use al generar simulacros.")
