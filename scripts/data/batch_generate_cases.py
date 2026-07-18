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

def batch_generate_cases():
    log("🚀 Iniciando generación masiva de CASOS DE ESTUDIO para Gestor III")
    
    USER_ID = 2
    keys = {"Mistral": get_api_key("Mistral")}
    if not keys["Mistral"]:
        log("❌ Error: Se requiere Mistral API Key para generar casos.")
        return

    gen = LLMGenerator("Mistral", keys["Mistral"], model_name="mistral-large-latest")
    
    db = SessionLocal()
    try:
        user_opec = db.query(UserOPEC).filter_by(user_id=USER_ID, is_active=True).first()
        if not user_opec:
            log("❌ Error: No se encontró OPEC activa.")
            return
        opec_topic = f"OPEC {user_opec.opec_number} - {user_opec.job_title}"
    finally:
        db.close()

    # Configuración de metas masivas
    TARGETS = [
        {"diff": 1, "count": 200, "label": "Fáciles"},
        {"diff": 2, "count": 200, "label": "Intermedias"},
        {"diff": 3, "count": 200, "label": "Difíciles"}
    ]
    
    total_q = 0
    total_cases_saved = 0

    for target in TARGETS:
        diff = target["diff"]
        label = target["label"]
        needed = target["count"]
        
        log(f"\n🌊 Iniciando lote de casos: {label} (Objetivo: {needed})")
        
        # Verificar progreso actual en DB para esta dificultad
        db = SessionLocal()
        current_count = db.query(CaseStudy).filter_by(difficulty=diff, topic=opec_topic).count()
        db.close()
        
        log(f"   📊 Progreso actual para {label}: {current_count}/{needed}")
        
        while current_count < needed:
            log(f"📦 [{label}] Generando Caso {current_count + 1}/{needed}...")
            
            try:
                case_data = gen.generate_case_study(opec_topic, num_questions=5, difficulty=diff)
                
                if not case_data or "questions" not in case_data:
                    raise Exception("La IA no devolvió un caso válido.")

                db = SessionLocal()
                # Crear Caso
                new_case = CaseStudy(
                    id=str(uuid.uuid4()),
                    title=case_data.get("title"),
                    text=case_data.get("text"),
                    difficulty=diff,
                    topic=opec_topic
                )
                db.add(new_case)
                
                # Crear Preguntas Asociadas
                for q in case_data.get("questions", []):
                    new_q = Question(
                        question_id=str(uuid.uuid4()),
                        case_id=new_case.id,
                        track=q.get("track", "FUNCIONAL"),
                        competency=q.get("competency", "General"),
                        topic=opec_topic,
                        difficulty=diff,
                        stem=q.get("stem"),
                        options_json=q.get("options"),
                        correct_key=q.get("correct_key"),
                        rationale=q.get("rationale"),
                        source_refs=f"IA (Mistral) - Caso Gestor III",
                        hash_norm=str(uuid.uuid4())
                    )
                    db.add(new_q)
                    total_q += 1
                
                db.commit()
                log(f"   ✅ Caso '{new_case.title}' guardado con {len(case_data.get('questions', []))} preguntas.")
                db.close()
                
                current_count += 1
                total_cases_saved += 1
                
                # Pequeña espera para no saturar la API
                time.sleep(2)

            except Exception as e:
                log(f"   ❌ Error en lote {label}: {e}")
                time.sleep(5) # Espera mayor tras error

    log(f"🏁 PROCESO COMPLETADO. Total: {total_cases_saved} casos y {total_q} preguntas generadas.")

if __name__ == "__main__":
    batch_generate_cases()
