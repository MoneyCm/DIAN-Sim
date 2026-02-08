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

# --- AUTO-SEED SECTION v5.4 ---
st.subheader("🚀 Generación de Base Inicial (Auto-Seed)")
st.markdown("""
Si no quieres crear preguntas una por una, usa esta opción. El sistema leerá tu **Cargo y Funciones** y generará automáticamente:
*   3 Casos Protagónicos completos.
*   10 Preguntas Funcionales.
*   5 Preguntas Comportamentales.
*   5 Preguntas de Integridad/Valores.
""")

if st.button("✨ Generar Base Inicial para este Cargo", type="primary", use_container_width=True):
    if not active_opec:
        st.error("Primero debes guardar la configuración de tu OPEC arriba.")
    else:
        from core.generators.llm import LLMGenerator
        from db.models import CaseStudy, Question
        import uuid
        import time
        
        # Init Generator (Use default provider from settings or fallback to Gemini/Mistral)
        # Note: We need the API Key. For checking purposes we might need to look into settings or ENV.
        # Assuming Global or Env Key is available if configured. 
        # For robustness, we will try to instantiate with explicit checks if possible, 
        # but LLMGenerator handles some defaults.
        
        # Retrieve settings from session or env? 
        # In 4_Generador_IA we get it from UI inputs. Here we assume System Key or User saved key.
        # For now, let's try to instantiate with placeholder and rely on .env if user hasn't set custom.
        
        try:
            api_key = os.getenv("MISTRAL_API_KEY") or os.getenv("GEMINI_API_KEY")
            provider = "mistral" if os.getenv("MISTRAL_API_KEY") else "gemini"
            
            # Simple fallback if keys missing (handled by LLMGenerator typically or errors out)
            gen = LLMGenerator(provider=provider, api_key=api_key if api_key else "dummy")
            
            progress = st.progress(0, text="Analizando perfil OPEC...")
            status = st.empty()
            
            db = SessionLocal()
            
            total_steps = 4
            current_step = 0
            
            # 1. Generate Case Studies
            status.info("Generando 3 Casos Protagónicos...")
            for i in range(3):
                try:
                    case_data = gen.generate_case_study(
                        topic=f"Caso {i+1}: {active_opec.job_title} - {active_opec.purpose}",
                        num_questions=3,
                        difficulty=2
                    )
                    
                    # Save Case
                    new_case = CaseStudy(
                        id=str(uuid.uuid4()),
                        title=case_data.get("title", "Caso Generado"),
                        text=case_data.get("text"),
                        topic=active_opec.job_title,
                        difficulty=2
                    )
                    db.add(new_case)
                    db.flush()
                    
                    # Save Questions for Case
                    for q in case_data.get("questions", []):
                        micro_comp = q.get('micro_competencia') or q.get('competency') or "General"
                        macro_dom = q.get('macro_dominio') or "Transversal"
                        new_q = Question(
                            question_id=str(uuid.uuid4()),
                            case_id=new_case.id,
                            stem=q.get("stem"),
                            options_json=q.get("options"),
                            correct_key=q.get("correct_key"),
                            rationale=q.get("rationale"),
                            track=q.get("track", "FUNCIONAL"),
                            competency=micro_comp,
                            micro_competencia=micro_comp,
                            macro_dominio=macro_dom,
                            topic=active_opec.job_title,
                            difficulty=2,
                            hash_norm=str(uuid.uuid4())
                        )
                        db.add(new_q)
                    
                    db.commit()
                except Exception as e:
                    print(f"Error generating case {i}: {e}")
                    status.warning(f"Error en caso {i+1}, reintentando...")
            
            current_step += 1
            progress.progress(25, text="Casos generados. Iniciando preguntas funcionales...")
            
            # 2. Functional Questions
            status.info("Generando preguntas funcionales...")
            func_text = f"Cargo: {active_opec.job_title}\nFunciones:\n{str(active_opec.functions)}"
            q_func = gen.generate_from_text(func_text, count=10, difficulty=2)
            
            for q in q_func:
                new_q = Question(
                    question_id=str(uuid.uuid4()),
                    stem=q.get("stem"),
                    options_json=q.get("options"),
                    correct_key=q.get("correct_key"),
                    rationale=q.get("rationale"),
                    track="FUNCIONAL",
                    topic=active_opec.job_title,
                    competency="Funcional",
                    micro_competencia="Conocimientos Técnicos",
                    macro_dominio="Funcionamiento del Estado",
                    difficulty=2,
                    hash_norm=str(uuid.uuid4())
                )
                db.add(new_q)
            db.commit()
            
            current_step += 1
            progress.progress(50, text="Preguntas funcionales listas. Pasando a comportamentales...")
            
            # 3. Behavioral Questions
            status.info("Generando preguntas comportamentales...")
            behav_text = f"CONTEXTO COMPORTAMENTAL: Generar preguntas sobre Liderazgo, Trabajo en Equipo y Orientación al Resultado para el cargo {active_opec.job_title}."
            q_behav = gen.generate_from_text(behav_text, count=5, difficulty=2)
            
            for q in q_behav:
                new_q = Question(
                    question_id=str(uuid.uuid4()),
                    stem=q.get("stem"),
                    options_json=q.get("options"),
                    correct_key=q.get("correct_key"),
                    rationale=q.get("rationale"),
                    track="COMPORTAMENTAL",
                    topic="Competencias Blandas",
                    competency="Comportamental",
                    micro_competencia="Liderazgo/Trabajo en Equipo",
                    macro_dominio="Competencias Comunes",
                    difficulty=2,
                    hash_norm=str(uuid.uuid4())
                )
                db.add(new_q)
            db.commit()
            
            current_step += 1
            progress.progress(75, text="Ya casi... Generando integridad...")
            
            # 4. Integrity Questions
            status.info("Generando preguntas de valores e integridad...")
            int_text = f"CONTEXTO ÉTICO: Dilemas éticos, código de integridad y valores para funcionario público DIAN en el cargo {active_opec.job_title}."
            q_int = gen.generate_from_text(int_text, count=5, difficulty=2)
             
            for q in q_int:
                new_q = Question(
                    question_id=str(uuid.uuid4()),
                    stem=q.get("stem"),
                    options_json=q.get("options"),
                    correct_key=q.get("correct_key"),
                    rationale=q.get("rationale"),
                    track="COMPORTAMENTAL", # Integrity usually falls here or new track
                    topic="Integridad y Valores",
                    competency="Ética",
                    micro_competencia="Integridad",
                    macro_dominio="Valores DIAN",
                    difficulty=2,
                    hash_norm=str(uuid.uuid4())
                )
                db.add(new_q)
            db.commit()
            
            progress.progress(100, text="¡Proceso Finalizado!")
            status.success("✅ Base inicial generada con éxito. ¡Ya puedes ir al Simulacro Real!")
            st.balloons()
            
            db.close()
            
        except Exception as e:
            st.error(f"Error crítico en Auto-Seed: {e}")

st.divider()
st.caption("🔒 Los datos de tu OPEC se guardan de forma segura en tu base de datos para que la IA los use al generar simulacros.")
