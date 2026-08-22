import streamlit as st
import os, sys, uuid
import math
import time

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
from ui_utils import get_db_info, load_css, log_ui_exception, metric_card, render_header

from core.auth import AuthManager
from core.competitions import get_active_competition_id
from core.generated_questions import candidate_issues, extract_candidates
from core.user_keys import get_user_key, save_user_key
from core.access_control import require_admin
from core.ai.usage_policy import AIUsageLimitError, reserve_ai_usage
from core.safe_uploads import (
    DEFAULT_DOCUMENT_LIMITS,
    UnsafeUpload,
    extract_pdf_pages,
    extract_text_file,
    sanitize_upload_name,
)
from core.learning.difficulty import difficulty_label, legacy_difficulty_to_editorial

# pass # Removed st.set_page_config

require_admin()

# --- v40: IA Limits Setup Mikey ---
from datetime import date
from core.auth import AuthManager
from services.stripe_service import StripeService
from db.models import UserStats

is_pro = AuthManager.is_pro()
can_generate = True
user_stats = None

if not is_pro:
    with SessionLocal() as db:
        user_stats = db.query(UserStats).filter_by(user_id=st.session_state["user_id"]).first()
        if user_stats:
            today = date.today()
            # Reset counter if new day
            if not user_stats.last_ia_date or user_stats.last_ia_date.date() < today:
                user_stats.ia_count_today = 0
                user_stats.last_ia_date = today
                db.commit()
            
            if user_stats.ia_count_today >= 3:
                can_generate = False

load_css()
render_header(title="Generador de preguntas con IA", subtitle="Crea candidatos desde una fuente y revísalos antes de incorporarlos al banco")

st.info(
    "La IA crea borradores, no preguntas confiables automáticamente. Cada candidato queda "
    "pendiente de revisión normativa antes de entrar al estudio activo."
)

with st.expander("🔐 Configuración de API Key", expanded=True):
    current_user_id = st.session_state.get("user_id")
    provider_options = ["Gemini", "Mistral", "OpenAI", "Groq"]
    configured = {
        item: bool(get_user_key(current_user_id, item) or get_api_key(item))
        for item in provider_options
    }
    default_provider = next((item for item in provider_options if configured[item]), "Gemini")
    col_prov, col_model = st.columns(2)
    with col_prov:
        provider = st.selectbox(
            "Proveedor",
            provider_options,
            index=provider_options.index(default_provider),
            format_func=lambda item: f"{item} {'· configurado' if configured[item] else '· sin clave'}",
        )
    
    with col_model:
        models_map = {
            "OpenAI": ["gpt-4o-mini", "gpt-4o"],
            "Gemini": ["gemini-2.5-flash", "gemini-flash-latest"],
            "Groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
            "Mistral": ["mistral-large-latest", "mistral-small-latest"]
        }
        model_name = st.selectbox("Modelo", models_map.get(provider, ["default"]))
        st.session_state["current_model"] = model_name
        st.session_state["current_provider"] = provider

    # Usar el nuevo sistema de carga persistente
    # Usar el nuevo sistema de carga persistente v5 (User-Secure)
    user_key_saved = get_user_key(current_user_id, provider) if current_user_id else None
    system_key_saved = get_api_key(provider) # Fallback system key
    
    # Logic: If user key exists, use it. If not, use system key.
    active_key_source = "Personal" if user_key_saved else ("Sistema" if system_key_saved else "Ninguna")
    effective_key_val = user_key_saved if user_key_saved else system_key_saved
    
    col_key, col_save_btn = st.columns([0.8, 0.2])
    
    with col_key:
        api_key_input = st.text_input(
            f"Nueva API Key de {provider}",
            value="",
            type="password",
            placeholder="Deja vacío para usar la clave ya configurada",
            help="Solo escribe una clave si deseas reemplazar la actual.",
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
    
    st.caption("🔒 Las claves personales se almacenan cifradas y el campo nunca muestra la clave guardada.")
    if provider == "Groq":
        st.warning("⚠️ **Nota Groq:** Límite gratuito diario muy estricto. Recomendamos Gemini.")
        
    # Ensure api_key is available for the generator logic below
    api_key = api_key_input.strip() or effective_key_val

st.divider()

col1, col2 = st.columns([1, 1])

with col1:
    
    # --- RECEPCIÓN DE REFUERZOS DESDE LA PRÁCTICA PJS CRONOMETRADA (v6.0) ---
    reinforcement_topic = st.session_state.get("ai_reinforcement_topic", None)
    reinforcement_source_context = st.session_state.get("ai_reinforcement_source_context", "")
    default_gen_idx = 1 if reinforcement_topic else 0 # 1 is Case Study
    
    # --- MODE SELECTION v5.0 ---
    generate_btn = False
    gen_mode = st.radio(
        "Modo de Generación",
        ["Preguntas desde Texto/PDF", "Caso PJS de práctica"],
        index=default_gen_idx,
        horizontal=True,
    )
    
    if gen_mode == "Preguntas desde Texto/PDF":
        if reinforcement_topic:
            st.success(f"🎯 **Modo Refuerzo Activado:** Se pre-configuró el tema **'{reinforcement_topic}'** basado en tus resultados del simulacro.")
        # Use a topic supplied by an explicit reinforcement flow; otherwise
        # leave it empty so an unrelated job title cannot override the
        # grounded topic returned by the generator.
        default_topic = st.session_state.get("ai_default_topic", "")
        custom_topic = st.text_input(
            "Tema normativo sustentado por la fuente (opcional)",
            value=default_topic,
            placeholder="Ej.: Facultades de fiscalización e investigación",
            help=(
                "Si lo completas, debe aparecer o estar claramente respaldado "
                "por el texto fuente. No uses aquí solamente el nombre del cargo."
            ),
        )
        
        num_q = st.select_slider(
            "Cantidad de preguntas",
            options=[1, 3, 5, 10, 15, 20],
            value=5,
            key="num_q_temp",
            help="Genera lotes pequeños para revisar mejor y evitar tiempos de espera.",
        )
        source_reference = st.text_input(
            "Referencia normativa de la fuente",
            placeholder="Ej.: Estatuto Tributario, artículo 684",
            help="Obligatoria para guardar. Identifica la norma, artículo o documento utilizado.",
        )
        
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
            uploaded_file = st.file_uploader(
                "Sube un documento (PDF, TXT)",
                type=["pdf", "txt"],
                help=(
                    f"PDF: máximo {DEFAULT_DOCUMENT_LIMITS.max_pdf_bytes // (1024 * 1024)} MB y "
                    f"{DEFAULT_DOCUMENT_LIMITS.max_pdf_pages} páginas. TXT: máximo "
                    f"{DEFAULT_DOCUMENT_LIMITS.max_text_bytes // (1024 * 1024)} MB."
                ),
            )
            if uploaded_file:
                try:
                    safe_upload_name = sanitize_upload_name(
                        uploaded_file.name, allowed_suffixes=(".pdf", ".txt")
                    )
                    upload_payload = bytes(uploaded_file.getbuffer())
                    if safe_upload_name.lower().endswith(".pdf"):
                        extracted = extract_pdf_pages(upload_payload)
                        st.session_state["ai_source_text"] = "\n".join(extracted)
                        st.success(f"PDF cargado: {len(extracted)} páginas leídas.")
                        st.rerun()
                    else:
                        st.session_state["ai_source_text"] = extract_text_file(upload_payload)
                        st.success("Archivo de texto cargado.")
                        st.rerun()
                except UnsafeUpload as exc:
                    st.error(str(exc))
                except Exception as exc:
                    log_ui_exception("generator.source_upload", exc)
                    st.error("No fue posible leer el archivo de forma segura.")
    
        with tab_json:
            st.info("💡 Usa esta opción si generaste las preguntas en **Gemini Web** usando el Mega-Prompt.")
            json_input = st.text_area("Pega aquí el JSON generado:", height=300, help="Copia todo el bloque JSON que te dio Gemini y pégalo aquí.")
            import_btn = st.button("🚀 Procesar e Importar JSON", use_container_width=True)
            
            if import_btn:
                # ... (Existing JSON logic kept identical, just indented) ...
                if not json_input:
                    st.warning("Pega el JSON primero.")
                else:
                    try:
                        data = repair_and_parse_json(json_input)
                        if not data:
                            st.error("Json Error")
                        else:
                            imported = extract_candidates(data, difficulty=2, source_ref=source_reference)
                            if imported:
                                st.session_state["generated_questions"] = imported
                                st.success(f"{len(imported)} candidato(s) importado(s) para revisión.")
                                st.rerun()
                            else:
                                st.error("El JSON no contiene preguntas reconocibles.")
                    except Exception as exc:
                        print(
                            f"AI JSON import failed: {type(exc).__name__}",
                            file=sys.stderr,
                        )
                        st.error("No se pudo importar el JSON. Revisa su estructura.")

        source_text = st.session_state.get("ai_source_text", "")
        char_count = len(source_text)
        st.caption(f"Caracteres detectados: {char_count}")
        raw_default_difficulty = int(st.session_state.get("ai_default_diff", 5) or 5)
        if 1 <= raw_default_difficulty <= 3:
            raw_default_difficulty = int(
                legacy_difficulty_to_editorial(raw_default_difficulty)
            )
        difficulty_value = st.slider(
            "Dificultad editorial",
            min_value=1,
            max_value=10,
            value=min(max(raw_default_difficulty, 1), 10),
            format="%d",
            help="Escala interna 1–10; no es una escala publicada por la CNSC.",
        )
        st.caption(
            f"Nivel {difficulty_value}: {difficulty_label(difficulty_value)} · "
            "complejidad editorial interna."
        )

        goa_mode = st.toggle(
            "📄 Generar preguntas situacionales",
            value=True,
            help="Si se desactiva, las preguntas serán técnicas directas en lugar de casos situacionales.",
        )
        
        if not can_generate:
            from ui_utils import render_paywall_card
            render_paywall_card("Generación de IA Ilimitada")
            st.warning(f"⚠️ Has agotado tus 3 generaciones gratuitas de hoy ({user_stats.ia_count_today}/3).")
            generate_btn = False
        else:
            if not is_pro:
                remaining_free = 3 - int(user_stats.ia_count_today or 0) if user_stats else 3
                st.caption(f"🎁 Te quedan **{remaining_free}** generaciones gratuitas hoy.")
            generate_btn = st.button("✨ Generar Preguntas", type="primary", use_container_width=True)

    else:
        # --- CASE STUDY MODE ---
        st.info(
            "🎭 **Modo caso PJS de práctica:** crea un escenario laboral y preguntas "
            "asociadas para entrenar análisis y lectura crítica."
        )
        
        # Pre-fill with reinforcement topic if available
        initial_cs_topic = reinforcement_topic if reinforcement_topic else "Procedimiento Tributario"
        cs_topic = st.text_input("Tema del Caso (Ej: Visita de Fiscalización, Atención a Usuario Agresivo)", value=initial_cs_topic)
        
        # Clear the reinforcement token so it doesn't stick forever if they change modes
        if reinforcement_topic and cs_topic != reinforcement_topic:
            st.session_state.pop("ai_reinforcement_topic", None)
            
        cs_num = 3
        st.caption("Formato de práctica recomendado: cada caso funcional contiene tres preguntas relacionadas. No sustituye el formato oficial que publique la CNSC.")
        cs_diff = st.slider(
            "Dificultad editorial del caso",
            1,
            10,
            5,
            help="Escala interna 1–10; no es una escala publicada por la CNSC.",
        )
        st.caption(f"Nivel {cs_diff}: {difficulty_label(cs_diff)}")
        
        generate_cs_btn = st.button("✨ Generar Caso Protagónico", type="primary", use_container_width=True)
        
        if generate_cs_btn:
             if not api_key:
                st.error("Falta API Key")
             elif reinforcement_topic and not reinforcement_source_context:
                st.error("No hay una fuente verificada para esta debilidad. Adjunta primero la norma oficial en modo Texto/PDF.")
             else:
                with st.spinner("Creando narrativa y preguntas..."):
                    reservation = None
                    started_case = time.perf_counter()
                    try:
                        case_planned_calls = 2 if provider.lower() == "gemini" else 1
                        reservation = reserve_ai_usage(
                            SessionLocal,
                            user_id=st.session_state.get("user_id"),
                            provider=provider,
                            model=model_name,
                            task_type="case_generation",
                            prompt=f"{cs_topic}\n{reinforcement_source_context}",
                            planned_calls=case_planned_calls,
                            prompt_version="case-generator-v1",
                        )
                        generator = LLMGenerator(provider, api_key, model_name=model_name)
                        result = generator.generate_case_study(
                            cs_topic,
                            cs_num,
                            cs_diff,
                            source_context=reinforcement_source_context,
                        )
                        reservation.finish(
                            success=True,
                            output_text=str(result),
                            latency_ms=int((time.perf_counter() - started_case) * 1000),
                        )
                        result["difficulty"] = cs_diff
                        st.session_state["generated_case"] = result
                        st.success("¡Caso Generado!")
                        st.rerun()
                    except AIUsageLimitError as exc:
                        st.warning(str(exc))
                    except Exception as exc:
                        log_ui_exception("generator.case.generate", exc)
                        if reservation is not None:
                            reservation.finish(
                                success=False,
                                latency_ms=int((time.perf_counter() - started_case) * 1000),
                                error=exc,
                            )
                        st.error("No fue posible generar el caso en este momento.")

    # Common Logic separation managed by flags or logic below

# --- v2.0 NEW: Sidebar Gamification Info ---
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
    elif not source_text or len(source_text) < 500:
        st.warning(
            "📋 El texto de origen es insuficiente. Aporta al menos 500 caracteres "
            "para sustentar un caso situacional sin inventar reglas o procedimientos."
        )
    elif not source_reference.strip():
        st.warning("📚 Indica la referencia normativa antes de generar preguntas.")
    else:
        with st.spinner("Analizando texto y creando preguntas... (Esto puede tardar unos segundos)"):
            reservation = None
            started_generation = time.perf_counter()
            try:
                calls_per_batch = 3 if provider.lower() == "gemini" else 1
                planned_calls = max(
                    1, math.ceil(int(num_q) / 5) * calls_per_batch
                )
                reservation = reserve_ai_usage(
                    SessionLocal,
                    user_id=st.session_state.get("user_id"),
                    provider=provider,
                    model=model_name,
                    task_type="question_generation",
                    prompt=source_text,
                    planned_calls=planned_calls,
                    prompt_version="question-generator-v1",
                )
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
                
                results = extract_candidates(
                    results, difficulty=difficulty_value, source_ref=source_reference
                )
                reservation.finish(
                    success=True,
                    output_text=str(results),
                    latency_ms=int((time.perf_counter() - started_generation) * 1000),
                )
                # Apply Custom Topic Override
                if results and custom_topic.strip():
                    for q in results:
                        q['topic'] = custom_topic.strip()
                        q['source_refs'] = source_reference.strip()
                
                st.session_state["generated_questions"] = results
                
                if not results:
                    st.error("No se pudieron generar preguntas. Revisa tu API Key o el formato del texto.")
                else:
                    # Incrementar contador mikey v4.0
                    if not is_pro and user_stats:
                        with SessionLocal() as db_upd:
                            # Re-fetch to avoid detached instance issues in some envs
                            st_upd = db_upd.query(UserStats).filter_by(id=user_stats.id).first()
                            st_upd.ia_count_today += 1
                            db_upd.commit()
                            
                    st.success(f"¡{len(results)} preguntas generadas!")
                    print(f"DEBUG: Generated {len(results)} questions for review.")
            except AIUsageLimitError as exc:
                st.warning(str(exc))
            except Exception as exc:
                log_ui_exception("generator.questions.generate", exc)
                if reservation is not None:
                    reservation.finish(
                        success=False,
                        latency_ms=int((time.perf_counter() - started_generation) * 1000),
                        error=exc,
                    )
                st.error("No fue posible generar preguntas en este momento.")
                print(f"DEBUG: Generation ERROR: {type(exc).__name__}")

# Create DB Session safely for checks
def check_duplicate(hash_norm):
    try:
        from db.session import SessionLocal
        db = SessionLocal()
        exists = db.query(Question).filter_by(hash_norm=hash_norm).first()
        db.close()
        return exists
    except Exception as exc:
        print(
            f"Duplicate check failed: {type(exc).__name__}", file=sys.stderr
        )
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
                
                candidate_difficulty = min(max(int(q.get("difficulty", 5) or 5), 1), 10)
                diff_tag = difficulty_label(candidate_difficulty)
                st.caption(f"{q['track']} | **{q.get('macro_dominio', 'Macro')}** > {q.get('micro_competencia', 'Micro')} | Dificultad editorial: {candidate_difficulty}/10 · {diff_tag}")
                
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
                issues = candidate_issues(
                    q,
                    st.session_state.get("ai_source_text", ""),
                    require_source_text=True,
                )
                if exists:
                    st.warning("⚠️ Ya existe en el banco.")
                elif issues:
                    st.error("No se puede guardar: " + "; ".join(issues))
                else:
                    if st.checkbox("Incluir en el guardado", key=f"save_{i}", value=True):
                        indices_to_save.append(i)
        
        st.divider()
        if st.button("💾 Guardar como candidatos pendientes", type="primary", use_container_width=True, disabled=not indices_to_save):
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
                            competition_id=get_active_competition_id(db, st.session_state.get("user_id")),
                            question_id=str(uuid.uuid4()),
                            track=data.get('track', 'FUNCIONAL'),
                            macro_dominio=data.get('macro_dominio'),
                            micro_competencia=data.get('micro_competencia'),
                            competency=data.get('micro_competencia', data.get('competency', 'General')),
                            topic=data.get('topic', 'Generado por IA'),
                            difficulty=min(max(round(int(data.get('difficulty', 5)) / 3), 1), 3),
                            stem=data.get('stem'),
                            options_json=data.get('options_json'),
                            correct_key=data.get('correct_key'),
                            rationale=data.get('rationale'),
                            source_refs=data.get('source_refs'),
                            question_type="SITUATIONAL" if str(data.get("stem", "")).upper().startswith("SITUACIÓN:") else "DIRECT",
                            is_verified=False,
                            quality_report={
                                "status": "PENDING_REVIEW",
                                "review": "reinforcement_candidate",
                                "origin": "ai_text_generator",
                                "provider": provider,
                                "model": model_name,
                                "editorial_difficulty_1_10": min(
                                    max(int(data.get("difficulty", 5) or 5), 1), 10
                                ),
                            },
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
                    
            except Exception as exc:
                db.rollback()
                st.error("❌ No fue posible guardar los candidatos en este momento.")
                print(
                    f"Candidate save failed: {type(exc).__name__}", file=sys.stderr
                )
            finally:
                db.close()
            
    if "generated_case" in st.session_state:
        st.write("---")
        st.subheader("2. Revisar y Guardar Caso Protagónico")
        
        case_data = st.session_state["generated_case"]
        from core.exam_format import is_official_functional_payload
        case_is_official = is_official_functional_payload(case_data)
        if not case_is_official:
            st.error("El caso no cumple el formato editorial configurado: esta plantilla exige 3 enunciados funcionales, cada uno con opciones A, B y C y una clave válida. La especificación PJS permite hasta 3 por caso.")
        else:
            st.warning("Candidato pendiente de revisión normativa. Guardarlo no lo habilita automáticamente para el simulacro ni el estudio activo.")
        
        with st.container(border=True):
            st.markdown(f"### 📂 {case_data.get('title', 'Sin Título')}")
            st.caption(f"Tema: {case_data.get('topic')} | Preguntas: {len(case_data.get('questions', []))}")
            st.markdown(f"_{case_data.get('text')}_")
            
            st.divider()
            
            for i, q in enumerate(case_data.get("questions", [])):
                with st.expander(f"Pregunta {i+1}: {q.get('stem')[:50]}...", expanded=False):
                    st.write(f"**Enunciado:** {q.get('stem')}")
                    st.write(f"**Opciones:** {q.get('options')}")
                    st.write(f"**Clave:** {q.get('correct_key')}")
                    st.write(f"**Justificación:** {q.get('rationale')}")

        if st.button("Guardar Caso en Banco", type="primary", use_container_width=True, disabled=not case_is_official):
            from db.session import SessionLocal
            from db.models import CaseStudy, Question
            import datetime
            import uuid
            
            db = SessionLocal()
            try:
                active_competition_id = get_active_competition_id(db, st.session_state.get("user_id"))
                # 1. Create Case
                new_case = CaseStudy(
                    id=str(uuid.uuid4()),
                    competition_id=active_competition_id,
                    title=case_data.get("title"),
                    text=case_data.get("text"),
                    topic=case_data.get("topic"),
                    difficulty=min(
                        max(round(int(case_data.get("difficulty", 5) or 5) / 3), 1),
                        3,
                    )
                )
                db.add(new_case)
                db.flush() # Get ID
                
                # 2. Create Questions linked to Case
                count_q = 0
                for q in case_data.get("questions", []):
                    # Ensure competency is not null (DB Constraint)
                    micro_comp = q.get('micro_competencia') or q.get('competency') or "General"
                    macro_dom = q.get('macro_dominio') or "Transversal"
                    question_hash = compute_hash(q.get("stem", ""))
                    if db.query(Question).filter_by(hash_norm=question_hash).first():
                        raise ValueError("El caso contiene una pregunta que ya existe en el banco.")
                    
                    new_q = Question(
                        competition_id=get_active_competition_id(db, st.session_state.get("user_id")),
                        question_id=str(uuid.uuid4()),
                        case_id=new_case.id, # LINKED
                        track=q.get("track", "FUNCIONAL"),
                        stem=q.get("stem"),
                        options_json=q.get("options"),
                        correct_key=q.get("correct_key"),
                        rationale=q.get("rationale"),
                        topic=case_data.get("topic"),
                        difficulty=min(
                            max(round(int(case_data.get("difficulty", 5) or 5) / 3), 1),
                            3,
                        ),
                        question_type="SITUATIONAL",
                        
                        # Fix NotNull Constraint (v5.3)
                        competency=micro_comp, 
                        micro_competencia=micro_comp,
                        macro_dominio=macro_dom,
                        
                        source_refs=q.get("source_ref") or reinforcement_source_context or "Candidato generado por IA",
                        is_verified=False,
                        quality_report={
                            "status": "PENDING_REVIEW",
                            "review": "reinforcement_candidate",
                            "weak_topic": reinforcement_topic,
                            "editorial_difficulty_1_10": min(
                                max(int(case_data.get("difficulty", 5) or 5), 1), 10
                            ),
                        },
                        hash_norm=question_hash
                    )
                    db.add(new_q)
                    count_q += 1
                
                db.commit()
                st.success(f"✅ ¡Caso '{new_case.title}' guardado con {count_q} preguntas!")
                st.balloons()
                del st.session_state["generated_case"]
                if st.button("Generar Otro"):
                    st.rerun()
                    
            except Exception as exc:
                db.rollback()
                print(f"Case save failed: {type(exc).__name__}", file=sys.stderr)
                st.error("No fue posible guardar el caso en este momento.")
            finally:
                db.close()

    elif "generated_questions" not in st.session_state:
        st.info("Las preguntas o casos generados aparecerán aquí para tu revisión.")

# Final page spacing
st.write("---")
