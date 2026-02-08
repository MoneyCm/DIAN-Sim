
import os
import sys
import time
import json
import uuid
import random
from dotenv import load_dotenv
from datetime import datetime

# Load env vars
load_dotenv()

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from db.models import Question, CaseStudy
from core.profiles import PROFILES
from core.dedupe import compute_hash

def generate_cases_protagonicos(target_cases=5):
    """
    Generates 'Casos Protagónicos': Long text + 3-5 related questions.
    """
    print(f"🚀 INICIANDO GENERACIÓN DE CASOS PROTAGÓNICOS: META {target_cases} CASOS")
    
    # Use the hardcoded key that worked previously if env var is missing
    key = os.getenv("MISTRAL_API_KEY", "mo22xN9XNmdNT1QHvp7LPKmu27KvmZ13")
    if not key:
        print("❌ Sin API Key")
        return

    try:
        from mistralai import Mistral
        # Use the resolved key
        client = Mistral(api_key=key)
        
        db = SessionLocal()
        
        # Prepare Topic Pool
        p = PROFILES["Gestor III (OPEC 236769)"]
        topics = []
        topics.extend(p["functional_tracks"]["FUNCIONAL"])
        
        total_created = 0
        
        while total_created < target_cases:
            topic = random.choice(topics)
            difficulty = 3 # Casos are usually hard
            
            prompt = f"""
            Actúa como Diseñador de Pruebas CNSC (Comisión Nacional del Servicio Civil).
            Genera UN (1) "CASO PROTAGÓNICO" completo para el perfil: Gestor III (Fiscalización).
            
            Tema Principal: {topic}
            
            Estructura Requerida:
            1. Un texto narrativo denso (300-400 palabras) que describa una situación compleja con múltiples variables (normativa, ética, procedimental, técnica).
            2. CINCO (5) preguntas de selección múltiple derivadas de ESE mismo texto.
            
            FORMATO JSON ÚNICO:
            {{
                "case_title": "Título del Caso",
                "case_text": "Texto completo de la situación...",
                "questions": [
                    {{
                        "stem": "Pregunta 1 relacionada con el texto...",
                        "options": {{"A": "...", "B": "...", "C": "... (Clave)", "D": "..."}},
                        "correct_key": "C",
                        "rationale": "Justificación basada en el texto y norma...",
                        "competency": "Competencia evaluada (ej. Análisis de Datos)"
                    }},
                    ... (4 more)
                ]
            }}
            """
            
            try:
                response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                data = json.loads(content)
                
                # Save Logic
                if "case_text" in data and "questions" in data:
                    # 1. Create Case
                    new_case = CaseStudy(
                        id=str(uuid.uuid4()),
                        title=data.get("case_title", f"Caso {topic}"),
                        text=data.get("case_text"),
                        difficulty=difficulty,
                        topic=topic,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_case)
                    db.flush() # Get ID
                    
                    # 2. Add Questions
                    for q_data in data["questions"]:
                        h = compute_hash(q_data.get("stem"))
                        q = Question(
                            question_id=str(uuid.uuid4()),
                            case_id=new_case.id, # LINKED!
                            track="CASO",
                            macro_dominio=topic,
                            micro_competencia=q_data.get("competency", "General"),
                            competency=q_data.get("competency", "General"),
                            topic=topic,
                            difficulty=difficulty,
                            stem=q_data.get("stem"),
                            options_json=q_data.get("options"),
                            correct_key=q_data.get("correct_key"),
                            rationale=q_data.get("rationale"),
                            source_refs="Gen Case Script",
                            created_at=datetime.utcnow(),
                            hash_norm=h
                        )
                        db.add(q)
                    
                    db.commit()
                    total_created += 1
                    print(f"✅ Caso Generado: {new_case.title} ({len(data['questions'])} preguntas)")
                    time.sleep(2)
                else:
                    print("⚠️ JSON incompleto, reintentando...")
            
            except Exception as e:
                print(f"❌ Error Generating Case: {e}")
                time.sleep(5)
                
        db.close()
        print("🏆 Generación de Casos Finalizada.")

    except Exception as e:
        print(f"❌ Error Fatal: {e}")

if __name__ == "__main__":
    # Generate just 2 for testing initially
    generate_cases_protagonicos(target_cases=2)
