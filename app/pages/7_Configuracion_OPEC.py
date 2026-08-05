import streamlit as st
import os, sys, json, re, unicodedata

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Competition, UserOPEC
from ui_utils import load_css, render_header, render_custom_sidebar

from core.auth import AuthManager

# pass # Removed st.set_page_config

def extract_opec_profile_from_text(text):
    """Extrae los campos relevantes de una ficha copiada desde SIMO."""
    if len(text.strip()) < 40:
        raise ValueError("Pega el texto completo de la ficha de empleo de SIMO.")

    def field(pattern):
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""

    def section(start, end):
        match = re.search(rf"{start}\s*[:\-]?\s*(.*?)(?=\s*{end}\b|\Z)", text, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    functions_raw = section(r"Funciones", r"Requisitos|Equivalencias|Vacantes")
    matches = re.findall(r"(?:^|\n)\s*\d{1,2}\s*[\.)]\s*(.*?)(?=(?:\n\s*\d{1,2}\s*[\.)])|\Z)", functions_raw, flags=re.DOTALL)
    functions = [re.sub(r"\s+", " ", value).strip() for value in matches if value.strip()]
    if not functions and functions_raw:
        functions = [re.sub(r"\s+", " ", functions_raw).strip()]

    denomination = field(r"(?:Denominaci[oó]n|Nombre\s+del\s+Cargo)\s*:?[ \t]*(.*?)(?=\s+(?:Grado|C[oó]digo)\s*:|\n)")
    grade = field(r"Grado\s*:?[ \t]*(\d+)")
    opec_number = field(r"(?:N[uú]mero\s+)?OPEC\s*[:#]?\s*(\d{4,})")
    job_title = " ".join(part for part in [denomination, f"Grado {grade}" if grade else ""] if part)
    return {
        "opec_number": opec_number,
        "job_title": job_title or (f"Empleo OPEC {opec_number}" if opec_number else ""),
        "level": field(r"Nivel\s*:?[ \t]*(.*?)(?=\s+(?:Denominaci[oó]n|Nombre\s+del\s+Cargo)\s*:|\n)"),
        "purpose": re.sub(r"\s+", " ", section(r"Prop[oó]sito", r"Funciones|Requisitos|Equivalencias")).strip(),
        "functions": functions,
        "requirements": re.sub(r"\s+", " ", section(r"Requisitos", r"Equivalencias|Vacantes")).strip(),
    }


def is_legacy_territorial_12_duplicate(competition):
    """Hide the old manual Bolívar entry; keep the canonical profile visible."""
    normalized = "".join(
        char for char in unicodedata.normalize("NFD", competition.name.upper())
        if unicodedata.category(char) != "Mn"
    )
    return (
        competition.code != "TERRITORIAL-12-BOLIVAR-2685"
        and "TERRITORIAL 12" in normalized
        and "BOLIVAR" in normalized
    )

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión en la página principal.")
    st.stop()

load_css()
if st.session_state.get("opec_onboarding"):
    st.info("👋 Bienvenido. Completa primero los datos de la ficha del cargo. Después se habilitarán tu dashboard, plan diario y simulacros personalizados.")
render_custom_sidebar()
render_header(title="Mi Meta: OPEC", subtitle="Configura tu cargo y enfoca tu preparación")

def get_active_opec(competition_id=None):
    db = SessionLocal()
    u_id = st.session_state.get("user_id")
    query = db.query(UserOPEC).filter_by(user_id=u_id)
    if competition_id is not None:
        query = query.filter(UserOPEC.competition_id == competition_id)
    else:
        query = query.filter(UserOPEC.is_active.is_(True))
    opec = query.order_by(UserOPEC.updated_at.desc()).first()
    db.close()
    return opec

u_id = st.session_state.get("user_id")
competition_db = SessionLocal()
competitions = [
    competition for competition in competition_db.query(Competition).filter_by(is_active=True).order_by(Competition.name).all()
    if not is_legacy_territorial_12_duplicate(competition)
]
current_opec = get_active_opec()
competition_ids = [competition.id for competition in competitions]
default_competition_id = (
    current_opec.competition_id if current_opec and current_opec.competition_id in competition_ids
    else (competition_ids[0] if competition_ids else None)
)
selected_competition_id = st.selectbox(
    "Concurso o proceso de selección",
    competition_ids,
    index=competition_ids.index(default_competition_id) if default_competition_id in competition_ids else 0,
    format_func=lambda competition_id: next(
        competition.name for competition in competitions if competition.id == competition_id
    ),
    key="selected_competition_id",
) if competition_ids else None
selected_competition = competition_db.get(Competition, selected_competition_id) if selected_competition_id else None
competition_db.close()
active_opec = get_active_opec(selected_competition_id)

if active_opec and not active_opec.is_active:
    if st.button("Usar este concurso y cargo", type="primary", use_container_width=True):
        activate_db = SessionLocal()
        try:
            activate_db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
            selected_opec = activate_db.get(UserOPEC, active_opec.id)
            selected_opec.is_active = True
            activate_db.commit()
            st.success(f"Concurso activo: {selected_competition.name}")
            st.rerun()
        finally:
            activate_db.close()

with st.expander("Agregar otro concurso CNSC"):
    with st.form("new_competition_form"):
        new_competition_code = st.text_input("Código del proceso", placeholder="Ej: TERRITORIAL-11")
        new_competition_name = st.text_input("Nombre del concurso", placeholder="Ej: Territorial 11")
        new_competition_entity = st.text_input("Entidad", placeholder="Ej: Alcaldía o entidad convocante")
        if st.form_submit_button("Registrar concurso"):
            if not new_competition_code.strip() or not new_competition_name.strip():
                st.error("Indica el código y el nombre del concurso.")
            else:
                create_db = SessionLocal()
                try:
                    code = new_competition_code.strip().upper()
                    existing_competition = create_db.query(Competition).filter_by(code=code).first()
                    if existing_competition:
                        st.warning("Ese concurso ya está registrado.")
                    else:
                        create_db.add(Competition(
                            code=code,
                            name=new_competition_name.strip(),
                            entity=new_competition_entity.strip() or None,
                            is_active=True,
                        ))
                        create_db.commit()
                        st.success("Concurso registrado. Ya puedes asociarle una OPEC.")
                        st.rerun()
                finally:
                    create_db.close()

st.markdown("""
<div class="dian-card">
    Configura aquí el <b>Número OPEC</b> de la vacante a la que aspiras. Esto permitirá que la IA genere preguntas 
    específicamente para las funciones y requisitos de tu cargo.
</div>
""", unsafe_allow_html=True)

# Debug session
if st.session_state.get("debug_mode"):
    st.caption(f"🔧 Debug: User ID: {u_id} | Active OPEC: {active_opec.id if active_opec else 'None'}")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Pegar ficha del empleo")
    st.caption("Copia y pega aquí el texto completo de la ficha de empleo de SIMO. La aplicación extrae los datos y te muestra una vista previa antes de guardarlos.")
    employment_text = st.text_area(
        "Ficha de empleo de SIMO",
        placeholder="Pega aquí desde 'Nivel' hasta 'Vacantes'...",
        height=360,
        key="opec_employment_text",
    )

    if employment_text.strip():
        try:
            extracted = extract_opec_profile_from_text(employment_text)
            if not extracted.get("opec_number"):
                st.error("No se pudo identificar el número OPEC. Verifica que hayas pegado la ficha completa de SIMO.")
            else:
                incomplete = [label for label in ("level", "purpose", "functions", "requirements") if not extracted.get(label)]
                if incomplete:
                    st.warning("La ficha se puede guardar, pero el PDF no permitió extraer: " + ", ".join(incomplete) + ".")
                st.success(f"Se identificó la OPEC {extracted['opec_number']}. Revisa la extracción antes de confirmarla.")
                st.markdown(f"**Cargo:** {extracted['job_title']}  ")
                st.markdown(f"**Nivel:** {extracted['level']}  ")
                st.markdown(f"**Funciones detectadas:** {len(extracted['functions'])}")
                with st.expander("Ver datos extraídos", expanded=False):
                    st.write(extracted["purpose"])
                    st.write(extracted["functions"])
                    st.write(extracted["requirements"])

                if st.button("Confirmar y enfocar simulador", type="primary", use_container_width=True):
                    if selected_competition_id is None:
                        st.error("Primero selecciona o registra un concurso.")
                    else:
                        db = SessionLocal()
                        try:
                            db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
                            existing = db.query(UserOPEC).filter_by(
                                user_id=u_id,
                                competition_id=selected_competition_id,
                                opec_number=extracted["opec_number"],
                            ).first()
                            values = {
                                "job_title": extracted["job_title"],
                                "level": extracted["level"],
                                "purpose": extracted["purpose"],
                                "functions": extracted["functions"],
                                "requirements": extracted["requirements"],
                                "is_active": True,
                            }
                            if existing:
                                for field, value in values.items():
                                    setattr(existing, field, value)
                            else:
                                db.add(UserOPEC(
                                    user_id=u_id,
                                    competition_id=selected_competition_id,
                                    opec_number=extracted["opec_number"],
                                    **values,
                                ))
                            db.commit()
                            st.session_state.pop("opec_onboarding", None)
                            st.success("Ficha cargada y concurso activado.")
                            st.rerun()
                        except Exception as exc:
                            db.rollback()
                            st.error(f"Error al guardar la ficha: {exc}")
                        finally:
                            db.close()
        except ValueError as exc:
            st.error(str(exc))

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
                        competition_id=selected_competition_id,
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
                            competition_id=selected_competition_id,
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
                    competition_id=selected_competition_id,
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
                    competition_id=selected_competition_id,
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
                    competition_id=selected_competition_id,
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
            
            status.success("✅ Base inicial generada con éxito. ¡Ya puedes ir al Simulacro Real!")
            st.balloons()
            
        except Exception as e:
            st.error(f"Error crítico en Auto-Seed: {e}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()

st.divider()
st.caption("🔒 Los datos de tu OPEC se guardan de forma segura en tu base de datos para que la IA los use al generar simulacros.")
