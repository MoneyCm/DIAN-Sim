import streamlit as st
import os, sys, uuid

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import Question
from core.generators.llm import LLMGenerator
from core.generators.utils import repair_and_parse_json
from core.dedupe import compute_hash
from core.config import get_api_key, save_api_key_local # NUEVO
from ui_utils import load_css, render_header, render_custom_sidebar, metric_card, get_db_info

import pypdf
import io

from core.auth import AuthManager

st.set_page_config(page_title="Generador IA | DIAN Sim", page_icon="🤖", layout="wide")

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión.")
    st.stop()

load_css()
render_header(title="Generador de Preguntas con IA v5.0", subtitle="Crea material de estudio a partir de documentos")

st.markdown("""
<div class="dian-card">
    Aquí puedes usar inteligencia artificial para crear preguntas a partir de tus propios documentos.
</div>
""", unsafe_allow_html=True)

with st.expander("🔐 Configuración de API Key", expanded=True):
    col_prov, col_model = st.columns(2)
    col_prov, col_model = st.columns(2)
    with col_prov:
        provider = st.selectbox("Proveedor", ["OpenAI", "Gemini", "Groq", "Mistral"])
    
    with col_model:
        models_map = {
            "OpenAI": ["gpt-4o-mini", "gpt-4o"],
            "Gemini": ["gemini-flash-latest", "gemini-2.0-flash-001", "gemini-pro-latest"],
            "Groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
            "Mistral": ["mistral-large-latest", "mistral-small-latest"]
        }
        model_name = st.selectbox("Modelo", models_map.get(provider, ["default"]))
        st.session_state["current_model"] = model_name
        st.session_state["current_provider"] = provider

    # Usar el nuevo sistema de carga persistente
    # Usar el nuevo sistema de carga persistente v5 (User-Secure)
    from core.user_keys import get_user_key, save_user_key
    
    current_user_id = st.session_state.get("user_id")
    user_key_saved = get_user_key(current_user_id, provider) if current_user_id else None
    system_key_saved = get_api_key(provider) # Fallback system key
    
    # Logic: If user key exists, use it. If not, use system key.
    active_key_source = "Personal" if user_key_saved else ("Sistema" if system_key_saved else "Ninguna")
    effective_key_val = user_key_saved if user_key_saved else system_key_saved
    
    col_key, col_save_btn = st.columns([0.8, 0.2])
    
    with col_key:
        api_key_input = st.text_input(
            f"API Key {provider}", 
            value=effective_key_val if effective_key_val else "", 
            type="password", 
            help="Tu llave se guarda ENCRIPTADA en tu cuenta Personal."
        )
        
        if active_key_source == "Personal":
            st.success(f"✅ Llave PERSONAL de {provider} cargada y encriptada.")
        elif active_key_source == "Sistema":
            st.info(f"🌎 Usando llave del SISTEMA (Global). Puedes sobreescribirla con una personal.")
        else:
            st.warning(f"⚠️ No hay llave configurada para {provider}.")
    
    with col_save_btn:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("💾 Guardar", help="Guardar llave personal encriptada"):
            if api_key_input:
                if current_user_id:
                    if save_user_key(current_user_id, provider, api_key_input):
                        st.success("¡Encriptada y Guardada!")
                        st.rerun()
                    else:
                        st.error("Error BD")
                else:
                    st.error("Debes iniciar sesión")
            else:
                st.warning("Escribe algo")
    
    st.caption("🔒 **Seguridad v5:** Tus llaves se cifran (Fernet 256-bit) y solo tú puedes usarlas.")
    if provider == "Groq":
        st.warning("⚠️ **Nota Groq:** Límite gratuito diario muy estricto. Recomendamos Gemini.")
        
    # Ensure api_key is available for the generator logic below
    api_key = api_key_input

st.divider()

col1, col2 = st.columns([1, 1])

with col1:
    # Move parameters ABOVE tabs to fix NameError in JSON Import Mikey v47.3.1
    # Pre-fill topic from session state if available 
    default_topic = st.session_state.get("ai_default_topic", "Gestor II")
    custom_topic = st.text_input("Etiqueta / Tema para estas preguntas (Ej: Gestor II)", value=default_topic)
    
    num_q = st.slider("Cantidad de preguntas a generar", 1, 100, 10, key="num_q_temp", help="Recomendado: 10-30 para máxima calidad y evitar errores de tiempo de espera.")
    
    tab_text, tab_file, tab_json = st.tabs(["📋 Pegar Texto", "📂 Subir Archivo", "🧩 Importar JSON"])
    
    # Persistent source text logic
    if "ai_source_text" not in st.session_state:
        st.session_state["ai_source_text"] = st.session_state.get("ai_default_text", "")
    
    with tab_text:
        # Fixed: Direct binding to key to avoid sync lag Mikey v6.2
        st.text_area("Pega aquí el artículo o ley:", 
                    key="ai_source_text", 
                    height=300)
            
    with tab_file:
        uploaded_file = st.file_uploader("Sube un documento (PDF, TXT)", type=["pdf", "txt"])
        if uploaded_file:
            try:
                if uploaded_file.type == "application/pdf":
                    reader = pypdf.PdfReader(uploaded_file)
                    extracted = []
                    for page in reader.pages:
                        extracted.append(page.extract_text())
                    st.session_state["ai_source_text"] = "\n".join(extracted)
                    st.success(f"PDF cargado: {len(reader.pages)} páginas leídas.")
                    st.rerun() # Force refresh for counter Mikey
                else:
                    # TXT
                    st.session_state["ai_source_text"] = uploaded_file.read().decode("utf-8")
                    st.success("Archivo de texto cargado.")
                    st.rerun() # Force refresh Mikey
            except Exception as e:
                st.error(f"Error leyendo archivo: {e}")

    with tab_json:
        st.info("💡 Usa esta opción si generaste las preguntas en **Gemini Web** usando el Mega-Prompt.")
        json_input = st.text_area("Pega aquí el JSON generado:", height=300, help="Copia todo el bloque JSON que te dio Gemini y pégalo aquí.")
        import_btn = st.button("🚀 Procesar e Importar JSON", use_container_width=True)
        
        if import_btn:
            if not json_input:
                st.warning("Pega el JSON primero.")
            else:
                try:
                    # Usamos la utilidad global para limpiar y parsear v48.2.1 Mikey
                    data = repair_and_parse_json(json_input)
                    
                    if not data:
                        st.error("No se pudo parsear el JSON. Asegúrate de copiar el bloque completo.")
                    else:
                        # Extraer preguntas (lógica similar a _generate_batch)
                        candidates = []
                        if isinstance(data, dict):
                            if "questions" in data:
                                candidates = data["questions"]
                            elif len(data.keys()) == 1:
                                candidates = list(data.values())[0]
                            else:
                                if "stem" in data:
                                    candidates = [data]
                        elif isinstance(data, list):
                            candidates = data
                        
                        if not candidates:
                            st.error("No se encontraron preguntas válidas en el JSON.")
                        else:
                            # Convertir al formato interno
                            import uuid
                            from core.dedupe import compute_hash
                            results = []
                            for item in candidates:
                                if not item.get("stem"): continue
                                results.append({
                                    "question_id": str(uuid.uuid4()),
                                    "track": item.get("track", "FUNCIONAL"),
                                    "macro_dominio": item.get("macro_dominio", "Transversal"),
                                    "micro_competencia": item.get("micro_competencia", item.get("competency", "General")),
                                    "topic": custom_topic.strip() if custom_topic.strip() else item.get("topic", "Importado"),
                                    "difficulty": item.get("difficulty", 2),
                                    "stem": item.get("stem"),
                                    "options_json": item.get("options"),
                                    "correct_key": item.get("correct_key"),
                                    "rationale": item.get("rationale"),
                                    "source_refs": "Importación Manual Gemini Web",
                                    "hash_norm": compute_hash(item.get("stem", ""))
                                })
                            
                            st.session_state["generated_questions"] = results
                            st.success(f"¡{len(results)} preguntas importadas con éxito! Revísalas a la derecha.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error procesando JSON: {e}")

    source_text = st.session_state["ai_source_text"]
    char_count = len(source_text)
    st.caption(f"Caracteres detectados: {char_count}")
    
    # v47 Coverage Indicator
    if char_count > 0:
        window_size = 18000
        overlap = 2000
        batch_size = 5
        est_batches = (num_q + batch_size - 1) // batch_size
        est_chars = est_batches * (window_size - overlap)
        coverage_pct = min(100, int((est_chars / char_count) * 100))
        
        if coverage_pct >= 100:
            st.success(f"🎯 **Cobertura Total:** Se analizará el 100% del documento.")
        else:
            st.info(f"🔍 **Cobertura de Muestreo:** Se analizará aprox. el {coverage_pct}% del documento.")

    difficulty_p_val = st.session_state.get("ai_default_diff", 2)
    inv_difficulty_map = {1: "Básico", 2: "Intermedio", 3: "Avanzado"}
    
    difficulty_map = {"Básico": 1, "Intermedio": 2, "Avanzado": 3}
    difficulty_label = st.select_slider("Nivel de dificultad", options=list(difficulty_map.keys()), value=inv_difficulty_map.get(difficulty_p_val, "Intermedio"))
    difficulty_value = difficulty_map[difficulty_label]
    
    goa_mode = st.toggle("📄 Aplicar Protocolo situacional GOA 2667 (Recomendado)", value=True, help="Si se desactiva, las preguntas serán técnicas directas en lugar de casos situacionales.")
    
    st.info("💡 Todas las preguntas generadas serán **SITUACIONALES** (casos prácticos) si el modo GOA está activo, cumpliendo con el estándar de evaluación de la DIAN.")
    
    # v47.2 Massive File Alert
    if char_count > 500000:
        st.warning(f"⚠️ **Archivo Masivo Detectado:** Tu documento tiene {char_count:,} caracteres. Los proveedores gratuitos (Gemini/Groq) pueden agotar su cuota rápidamente. **Recomendación:** Genera lotes de máximo 10-15 preguntas a la vez.")
    
    st.caption("💎 **Tip Pro v47.2:** El motor 'Escudo Supernova' ahora comprime el contexto en archivos gigantes (>1M) para evitar bloqueos y respeta los tiempos de espera sugeridos por Google.")
    
    generate_btn = st.button("✨ Generar Preguntas", type="primary", use_container_width=True)

# --- v2.0 NEW: Sidebar Gamification Info ---
stats_s, rank = render_custom_sidebar()
total_q, current_db = get_db_info()

st.sidebar.markdown(f"""
<div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid var(--dian-red);">
    <b>Banco:</b> {total_q} Qs<br>
    <b>DB:</b> {current_db}
</div>
""", unsafe_allow_html=True)

if generate_btn:
    if not api_key:
        st.error("🔑 Falta la API Key. Por favor, ingrésala en la sección de configuración arriba.")
    elif not source_text or len(source_text) < 10:
        st.warning("📋 El texto de origen está vacío o es muy corto. Pega algún contenido o sube un archivo para generar preguntas.")
    else:
        with st.spinner("Analizando texto y creando preguntas... (Esto puede tardar unos segundos)"):
            try:
                generator = LLMGenerator(provider, api_key, model_name=model_name, goa_mode=goa_mode)
                
                # Progress simulation/placeholder Mikey
                prog_bar = st.progress(0, text="Iniciando generación masiva...")
                
                # Monkey patch or modify to accept progress callback? 
                # Better: LLMGenerator is already efficient. Let's just run it.
                # Since LLMGenerator.generate_from_text is synchronous and slow, 
                # we can't easily update the bar from inside without a callback.
                
                # Resilient Call Mikey v31
                try:
                    results = generator.generate_from_text(
                        source_text, 
                        num_q, 
                        difficulty=difficulty_value, 
                        progress_callback=prog_bar.progress,
                        user_id=st.session_state.get("user_id")
                    )
                except TypeError as te:
                    if "unexpected keyword argument" in str(te):
                        print("⚠️ [v31] Fallback: El servidor aún tiene llm.py en caché. Mikey")
                        results = generator.generate_from_text(source_text, num_q, difficulty=difficulty_value)
                    else:
                        raise te
                
                prog_bar.progress(100, text="¡Generación completada!")
                
                # Apply Custom Topic Override
                if results and custom_topic.strip():
                    for q in results:
                        q['topic'] = custom_topic.strip()
                
                st.session_state["generated_questions"] = results
                
                if not results:
                    st.error("No se pudieron generar preguntas. Revisa tu API Key o el formato del texto.")
                else:
                    st.success(f"¡{len(results)} preguntas generadas!")
                    print(f"DEBUG: Generated {len(results)} questions for review.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                print(f"DEBUG: Generation ERROR: {e}")

# Create DB Session safely for checks
def check_duplicate(hash_norm):
    try:
        from db.session import SessionLocal
        db = SessionLocal()
        exists = db.query(Question).filter_by(hash_norm=hash_norm).first()
        db.close()
        return exists
    except Exception as e:
        print(f"DEBUG: Error checking duplicate: {e}")
        return None

with col2:
    st.subheader("2. Revisar y Guardar")
    if "generated_questions" in st.session_state and st.session_state["generated_questions"]:
        candidates = st.session_state["generated_questions"]
        
        # Action Bar
        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            if st.button("🗑️ Descartar Todo", use_container_width=True):
                del st.session_state["generated_questions"]
                st.rerun()
        
        indices_to_save = []
        
        # Display candidates
        for i, q in enumerate(candidates):
            with st.container(border=True):
                # Header with Discard button
                header_col, discard_col = st.columns([0.85, 0.15])
                with header_col:
                    st.write(f"**Pregunta {i+1}**")
                with discard_col:
                    if st.button("❌", key=f"discard_{i}", help="Eliminar de esta lista"):
                        st.session_state["generated_questions"].pop(i)
                        st.rerun()

                st.write(f"**{q['stem']}**")
                
                diff_labels = {1: "🟢 Básico", 2: "🟡 Intermedio", 3: "🔴 Avanzado"}
                diff_tag = diff_labels.get(q.get('difficulty', 2), "Intermedio")
                st.caption(f"{q['track']} | **{q.get('macro_dominio', 'Macro')}** > {q.get('micro_competencia', 'Micro')} | Dificultad: {diff_tag}")
                
                # Show Options
                ops = q.get('options_json', {})
                if ops:
                    cols_ops = st.columns(min(3, len(ops)))
                    for idx, (k, v) in enumerate(ops.items()):
                        cols_ops[idx % 3].text(f"{k}) {v}")
                
                st.markdown(f"<span style='color: #4CAF50; font-weight: bold;'>Respuesta Correcta: {q['correct_key']}</span>", unsafe_allow_html=True)
                
                if q.get('rationale'):
                    with st.expander("Ver Justificación"):
                        st.write(q['rationale'])
                
                # Check Duplicates
                exists = check_duplicate(q['hash_norm'])
                if exists:
                    st.warning("⚠️ Ya existe en el banco.")
                else:
                    if st.checkbox("Incluir en el guardado", key=f"save_{i}", value=True):
                        indices_to_save.append(i)
        
        st.divider()
        if st.button("💾 Guardar Seleccionadas en Banco", type="primary", use_container_width=True, disabled=not indices_to_save):
            from db.session import SessionLocal
            import datetime
            db = SessionLocal()
            saved_count = 0
            already_exists = 0
            try:
                local_seen_hashes = set()
                for i in indices_to_save:
                    data = candidates[i]
                    h = data.get('hash_norm')
                    
                    if h in local_seen_hashes:
                        already_exists += 1
                        continue
                    
                    existing = db.query(Question).filter_by(hash_norm=h).first()
                    if not existing:
                        new_q = Question(
                            question_id=str(uuid.uuid4()),
                            track=data.get('track', 'FUNCIONAL'),
                            macro_dominio=data.get('macro_dominio'),
                            micro_competencia=data.get('micro_competencia'),
                            competency=data.get('micro_competencia', data.get('competency', 'General')),
                            topic=data.get('topic', 'Generado por IA'),
                            difficulty=data.get('difficulty', 2),
                            stem=data.get('stem'),
                            options_json=data.get('options_json'),
                            correct_key=data.get('correct_key'),
                            rationale=data.get('rationale'),
                            source_refs=data.get('source_refs', 'IA'),
                            created_at=datetime.datetime.utcnow(),
                            hash_norm=h
                        )
                        db.add(new_q)
                        local_seen_hashes.add(h)
                        saved_count += 1
                        print(f"DEBUG: Saving question to DB: {new_q.stem[:50]}...")
                    else:
                        already_exists += 1
                
                if saved_count > 0:
                    db.commit()
                    st.success(f"✅ ¡Éxito! Se guardaron **{saved_count}** preguntas nuevas en el banco.")
                    if already_exists > 0:
                        st.info(f"ℹ️ {already_exists} preguntas fueron omitidas porque ya existían.")
                    st.balloons()
                    
                    # Instead of immediate rerun, clear the candidates list but stay on page to show message
                    del st.session_state["generated_questions"]
                    st.info("Carga el banco o inicia un nuevo simulacro para verlas.")
                    if st.button("Volver a empezar"):
                        st.rerun()
                else:
                    st.warning("⚠️ No se guardaron preguntas nuevas. Todas las seleccionadas ya existen en el banco.")
                    
            except Exception as e:
                db.rollback()
                st.error(f"❌ Error al guardar en la base de datos: {str(e)}")
                print(f"CRITICAL ERROR SAVING: {e}")
            finally:
                db.close()
            
    else:
        st.info("Las preguntas generadas aparecerán aquí para tu revisión.")

# Final page spacing
st.write("---")
