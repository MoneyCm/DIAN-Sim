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
    log("🚀 Iniciando proceso de generación masiva (600 preguntas) con TRIPLE RESILIENCIA (Gemini, Mistral, Groq)")
    
    # Configuration
    USER_ID = 2 
    
    # Setup Providers
    providers = []
    keys = {
        "Gemini": get_api_key("Gemini"),
        "Mistral": get_api_key("Mistral"),
        "Groq": get_api_key("Groq")
    }
    
    gens = {}
    if keys["Gemini"]: gens["Gemini"] = LLMGenerator("Gemini", keys["Gemini"], model_name="gemini-1.5-flash")
    if keys["Mistral"]: gens["Mistral"] = LLMGenerator("Mistral", keys["Mistral"], model_name="mistral-large-latest")
    if keys["Groq"]: gens["Groq"] = LLMGenerator("Groq", keys["Groq"], model_name="llama-3.3-70b-versatile")
    
    available_providers = list(gens.keys())
    if not available_providers:
        log("❌ Error fatal: No hay API Keys configuradas.")
        return

    log(f"🔗 Proveedores activos: {', '.join(available_providers)}")

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
        {"diff": 1, "count": 166, "label": "Fáciles"},
        {"diff": 2, "count": 167, "label": "Intermedias"},
        {"diff": 3, "count": 167, "label": "Difíciles"}
    ]
    
    # State
    provider_idx = 0
    total_generated = 0
    
    for target in TARGETS:
        needed = target["count"]
        diff = target["diff"]
        label = target["label"]
        log(f"\n🌊 Iniciando lote: {label} (Objetivo: {needed})")
        
        # Check current progress in DB to resume
        db = SessionLocal()
        sources = [f"IA ({p}) - OPEC 236739" for p in available_providers]
        current_in_db = db.query(Question).filter(
            Question.source_refs.in_(sources),
            Question.difficulty == diff
        ).count()
        db.close()
        
        current_count = current_in_db
        log(f"   📊 Progreso actual para {label}: {current_count}/{needed}")
        
        batch_size = 5
        
        while current_count < needed:
            p_name = available_providers[provider_idx]
            current_generator = gens[p_name]
            
            try:
                func_block = " ".join(opec_funcs[:5]) if opec_funcs else opec_purpose
                synthetic_text = f"PERFIL: {opec_info}\nPROPÓSITO: {opec_purpose}\nFUNCIONES: {func_block}\nGenerar preguntas situacionales."
                
                log(f"   ⏳ [{p_name}] Generando sub-lote de {batch_size}...")
                
                questions = current_generator._generate_batch(synthetic_text, count=batch_size, difficulty=diff)
                
                if not questions:
                    raise Exception("La IA no devolvió preguntas (Posible bloqueo o error de formato)")
                
                # Save to DB
                db = SessionLocal()
                saved_batch = 0
                for q_data in questions:
                    h = q_data.get("hash_norm")
                    if not h: continue
                    
                    existing = db.query(Question).filter_by(hash_norm=h).first()
                    if not existing:
                        new_q = Question(
                            question_id=str(uuid.uuid4()),
                            track='FUNCIONAL',
                            competency=q_data.get('micro_competencia', 'General'),
                            topic=f"OPEC {user_opec.opec_number} - {q_data.get('micro_competencia', 'General')}",
                            difficulty=diff,
                            stem=q_data.get('stem'),
                            options_json=q_data.get('options_json'),
                            correct_key=q_data.get('correct_key'),
                            rationale=q_data.get('rationale'),
                            source_refs=f"IA ({p_name}) - OPEC 236739",
                            created_at=datetime.datetime.utcnow(),
                            hash_norm=h,
                            is_verified=True
                        )
                        db.add(new_q)
                        saved_batch += 1
                
                db.commit()
                db.close()
                
                current_count += saved_batch
                total_generated += saved_batch
                log(f"   ✅ [{p_name}] Guardadas {saved_batch}. Total: {current_count}/{needed}")
                
                # Wait based on provider
                time.sleep(2 if p_name == "Gemini" else 1)

            except Exception as e:
                error_msg = str(e).lower()
                log(f"   ❌ Error con {p_name}: {error_msg[:150]}")
                
                # Broad Switching Condition
                # If Gemini fails for ANY reason (429, 404, or internal "falla total"), we rotate.
                # If we've rotated through all and still fail, we wait.
                
                provider_idx = (provider_idx + 1) % len(available_providers)
                new_p = available_providers[provider_idx]
                
                if provider_idx == 0: # We looped back to the first one
                    log(f"   ⚠️ Ciclo completo de proveedores sin éxito. Esperando 60s antes de reintentar con {new_p}...")
                    time.sleep(60)
                else:
                    log(f"   🔄 Saltando a {new_p}...")
                    time.sleep(5)
                
    log(f"\n🏁 PROCESO COMPLETADO. Total generado: {total_generated} preguntas.")

if __name__ == "__main__":
    batch_generate()
