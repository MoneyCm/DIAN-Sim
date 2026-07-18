import os
import sys
import time
import uuid
import datetime
from sqlalchemy import text
from db.session import SessionLocal
from db.models import CaseStudy, Question, UserOPEC
from core.generators.llm import LLMGenerator
from core.config import get_api_key

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open("cases_generation.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def batch_generate_custom():
    log("🚀 Iniciando generación masiva: 10 Fáciles, 10 Medios, 10 Difíciles")
    
    USER_ID = 2
    mistral_key = get_api_key("Mistral")
    if not mistral_key:
        log("❌ Error: No se encontró la API Key de Mistral.")
        return

    gen = LLMGenerator("Mistral", mistral_key, model_name="mistral-large-latest")
    
    # Configuración de los lotes
    TARGETS = [
        {"diff": 1, "count": 5, "label": "Fáciles"},
        {"diff": 2, "count": 5, "label": "Intermedias"},
        {"diff": 3, "count": 5, "label": "Difíciles"}
    ]
    
    db = SessionLocal()
    try:
        user_opec = db.query(UserOPEC).filter_by(user_id=USER_ID).first()
        if not user_opec:
            log("❌ Error: No se encontró la OPEC del usuario.")
            return
        
        opec_topic = f"OPEC {user_opec.opec_number} - {user_opec.job_title}"
        log(f"📝 Tópico Base: {opec_topic}")
 
        total_saved = 0
        for target in TARGETS:
            diff = target["diff"]
            label = target["label"]
            needed = target["count"]
            
            log(f"\n--- Generando {needed} casos {label} (Dificultad {diff}) ---")
            
            for i in range(needed):
                log(f"📦 [{label}] Caso {i+1}/{needed}...")
                try:
                    case_data = gen.generate_case_study(opec_topic, num_questions=4, difficulty=diff)
                    
                    new_case = CaseStudy(
                        id=str(uuid.uuid4()),
                        title=case_data.get("title"),
                        text=case_data.get("text"),
                        difficulty=diff,
                        topic=opec_topic
                    )
                    db.add(new_case)
                    
                    for q in case_data.get("questions", []):
                        new_q = Question(
                            question_id=str(uuid.uuid4()),
                            case_id=new_case.id,
                            track=q.get("track", "FUNCIONAL"),
                            competency=q.get("competency", "Técnica/Fiscalización"),
                            topic=opec_topic,
                            difficulty=diff,
                            stem=q.get("stem"),
                            options_json=q.get("options"),
                            correct_key=q.get("correct_key"),
                            rationale=q.get("rationale"),
                            source_refs=f"Mistral - Batch Gen v20",
                            hash_norm=str(uuid.uuid4())
                        )
                        db.add(new_q)
                    
                    db.commit()
                    log(f"   ✅ Guardado: '{new_case.title}'")
                    total_saved += 1
                    time.sleep(1) # Pequeño respiro para la API
                except Exception as e:
                    log(f"   ❌ Error: {e}")
                    db.rollback()
                    time.sleep(5)
                    
        log(f"🏁 PROCESO COMPLETADO. Total: {total_saved} nuevos casos en Neon.")
        
    finally:
        db.close()

if __name__ == "__main__":
    batch_generate_custom()
