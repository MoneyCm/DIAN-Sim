import os
import sys
import time
import uuid
import datetime
import json
from db.session import SessionLocal
from db.models import CaseStudy, Question, UserOPEC
from core.generators.llm import LLMGenerator
from core.config import get_api_key

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open("cases_generation.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def generate_initial_cases():
    log("🚀 Generando LOTE INICIAL de 5 CASOS DE ESTUDIO para Gestor III (DIAN)")
    
    USER_ID = 1 # Usar ID del admin habitualmente
    mistral_key = get_api_key("Mistral")
    if not mistral_key:
        log("❌ Error: No se encontró la API Key de Mistral.")
        return

    gen = LLMGenerator("Mistral", mistral_key, model_name="mistral-large-latest")
    
    db = SessionLocal()
    try:
        user_opec = db.query(UserOPEC).filter_by(user_id=USER_ID, is_active=True).first()
        if not user_opec:
            user_opec = db.query(UserOPEC).first() # Fallback
        
        opec_topic = f"OPEC {user_opec.opec_number} - {user_opec.job_title}"
        diff = 3 # Nivel Profesional (3)
        
        log(f"📝 Tópico: {opec_topic} | Nivel: {diff}")
        
        for i in range(5):
            log(f"📦 Generando Caso {i+1}/5...")
            try:
                case_data = gen.generate_case_study(opec_topic, num_questions=5, difficulty=diff)
                
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
                        competency=q.get("competency", "Fiscalización"),
                        topic=opec_topic,
                        difficulty=diff,
                        stem=q.get("stem"),
                        options_json=q.get("options"),
                        correct_key=q.get("correct_key"),
                        rationale=q.get("rationale"),
                        source_refs=f"Mistral - Inicial DIAN",
                        hash_norm=str(uuid.uuid4())
                    )
                    db.add(new_q)
                
                db.commit()
                log(f"   ✅ Caso '{new_case.title}' guardado exitosamente.")
                time.sleep(2)
            except Exception as e:
                log(f"   ❌ Error en caso {i+1}: {e}")
                
    finally:
        db.close()

if __name__ == "__main__":
    generate_initial_cases()
