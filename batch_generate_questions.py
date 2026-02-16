import os
import sys
import time
import uuid
import datetime
import json
from db.session import SessionLocal
from db.models import Question, UserOPEC
from core.generators.llm import LLMGenerator
from core.config import get_api_key

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open("generation_progress.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def batch_generate():
    log("🚀 Iniciando proceso de generación masiva (600 preguntas) con RESILIENCIA MISTRAL")
    
    # Configuration
    USER_ID = 2 
    
    # Setup Providers
    gemini_key = get_api_key("Gemini")
    mistral_key = get_api_key("Mistral")
    
    gen_gemini = LLMGenerator("Gemini", gemini_key, model_name="gemini-1.5-flash") if gemini_key else None
    # Mistral Large requires paid tier sometimes, let's try mistral-large-latest or open-mistral-nemo if available, 
    # but the library usually handles defaults. Sticking to class defaults.
    gen_mistral = LLMGenerator("Mistral", mistral_key, model_name="mistral-large-latest") if mistral_key else None
    
    if not gen_gemini and not gen_mistral:
        log("❌ Error fatal: No hay API Keys configuradas ni para Gemini ni Mistral.")
        return

    # Check Target OPEC
    db = SessionLocal()
    try:
        user_opec = db.query(UserOPEC).filter_by(user_id=USER_ID, is_active=True).first()
        if not user_opec:
            log("❌ Error: No se encontró OPEC activa para el usuario.")
            return
            
        opec_info = f"{user_opec.opec_number} - {user_opec.job_title}"
        opec_purpose = user_opec.purpose
        opec_funcs = user_opec.functions or []
        log(f"🎯 OPEC Objetivo: {opec_info}")
    finally:
        db.close()

    # Targets
    TARGETS = [
        {"diff": 1, "count": 200, "label": "Fáciles"},
        {"diff": 2, "count": 200, "label": "Intermedias"},
        {"diff": 3, "count": 200, "label": "Difíciles"}
    ]
    
    # State Management
    current_generator = gen_gemini if gen_gemini else gen_mistral
    provider_name = "Gemini" if gen_gemini else "Mistral"
    
    total_generated = 0
    
    for target in TARGETS:
        needed = target["count"]
        diff = target["diff"]
        label = target["label"]
        log(f"\n🌊 Iniciando lote: {label} (Objetivo: {needed})")
        
        current_count = 0
        batch_size = 5 # Reduced batch size for stability with multiple providers
        
        while current_count < needed:
            try:
                # Rotate function focus
                func_block = " ".join(opec_funcs[:5]) if opec_funcs else opec_purpose
                
                synthetic_text = f"""
                CONTEXTO ESPECÍFICO PARA GENERACIÓN DE PREGUNTAS:
                PERFIL: {opec_info}
                PROPÓSITO: {opec_purpose}
                FUNCIONES CLAVE Y TEMAS A EVALUAR HOY:
                {func_block}
                NORMATIVA APLICABLE:
                - Estatuto Tributario Nacional
                - Código de Procedimiento Administrativo (CPACA)
                - Constitución Política de Colombia
                - Código General Disciplinario (Ley 1952)
                OBJETIVO:
                Generar preguntas situacionales.
                """
                
                log(f"   ⏳ Generando sub-lote de {batch_size} preguntas con {provider_name}...")
                
                # EXECUTE GENERATION
                questions = current_generator._generate_batch(synthetic_text, count=batch_size, difficulty=diff)
                
                if not questions:
                    log(f"   ⚠️ {provider_name} no devolvió preguntas. Reintentando...")
                    time.sleep(2)
                    continue
                
                # Save to DB
                db = SessionLocal()
                saved_batch = 0
                seen_hashes = set()
                
                for q_data in questions:
                    if "Generado" in q_data.get("topic", ""):
                        q_data["topic"] = f"OPEC {user_opec.opec_number} - {q_data.get('micro_competencia', 'General')}"
                    
                    h = q_data.get("hash_norm")
                    if h in seen_hashes: continue
                    
                    existing = db.query(Question).filter_by(hash_norm=h).first()
                    if not existing:
                        new_q = Question(
                            question_id=str(uuid.uuid4()),
                            track=q_data.get('track', 'FUNCIONAL'),
                            macro_dominio=q_data.get('macro_dominio', 'Transversal'),
                            micro_competencia=q_data.get('micro_competencia', 'General'),
                            competency=q_data.get('competency', 'General'),
                            topic=q_data.get('topic', 'Generado por IA'),
                            difficulty=q_data.get('difficulty', diff),
                            stem=q_data.get('stem'),
                            options_json=q_data.get('options_json'),
                            correct_key=q_data.get('correct_key'),
                            rationale=q_data.get('rationale'),
                            source_refs=f"IA ({provider_name}) - OPEC 236739",
                            created_at=datetime.datetime.utcnow(),
                            hash_norm=h,
                            is_verified=True
                        )
                        db.add(new_q)
                        saved_batch += 1
                        seen_hashes.add(h)
                
                db.commit()
                db.close()
                
                current_count += saved_batch
                total_generated += saved_batch
                log(f"   ✅ Guardadas {saved_batch} preguntas ({provider_name}). Progreso: {current_count}/{needed}")
                
                 # Dynamic Sleep based on provider
                if provider_name == "Gemini":
                    time.sleep(2)  # Fast
                else:
                    time.sleep(1) # Mistral is usually fast too but safer to wait

            except Exception as e:
                error_msg = str(e).lower()
                log(f"   ❌ Error con {provider_name}: {str(e)[:100]}...")
                
                # SWITCHING LOGIC
                if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg or "multiturn" in error_msg:
                    log("   ⚠️ Rate Limit detectado.")
                    
                    if provider_name == "Gemini" and gen_mistral:
                        log("   🔄 CAMBIANDO PROVEEDOR: Gemini -> Mistral")
                        current_generator = gen_mistral
                        provider_name = "Mistral"
                        time.sleep(2) # Switch delay
                        continue
                        
                    elif provider_name == "Mistral" and gen_gemini:
                        log("   🔄 CAMBIANDO PROVEEDOR: Mistral -> Gemini (Esperando enfriamiento)")
                        time.sleep(30) # Cool down Gemini
                        current_generator = gen_gemini
                        provider_name = "Gemini"
                        continue
                        
                    else:
                        log("   ⛔ Ambos proveedores saturados. Esperando 60s...")
                        time.sleep(60)
                else:
                    # Non-rate limit error, maybe content error or network
                     time.sleep(5)
                
    log(f"\n🏁 PROCESO COMPLETADO. Total generado: {total_generated} preguntas.")

if __name__ == "__main__":
    batch_generate()
