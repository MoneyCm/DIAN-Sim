
import os
import sys
import time
import json
import uuid
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime

# Load env vars
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import SessionLocal
from db.models import Question
from core.dedupe import compute_hash

def populate_exact_opec(target_total=30):
    print(f"🚀 Generando 30 preguntas exclusivas para OPEC 236739 (Petición Usuario)...")
    db: Session = SessionLocal()
    
    total_new = 0
    batch_size = 5
    mistral_key = os.getenv("MISTRAL_API_KEY", "mo22xN9XNmdNT1QHvp7LPKmu27KvmZ13")
    
    # EXACT OPEC Data from User
    opec_data = {
        "opec_number": "236739",
        "job_title": "GESTOR III (FISCALIZACIÓN/LIQUIDACIÓN)",
        "functions": [
            "PROFERIR ACTOS ADMINISTRATIVOS DE DETERMINACIÓN DE TRIBUTOS",
            "RESOLVER RECURSOS EN LA VÍA GUBERNATIVA",
            "ADELANTAR INVESTIGACIONES TRIBUTARIAS PROFUNDAS"
        ]
    }

    try:
        from mistralai import Mistral
        client = Mistral(api_key=mistral_key)
        
        while total_new < target_total:
            print(f"   ⚗️ Cocinando lote para {opec_data['opec_number']}... ({total_new}/{target_total})")
            
            prompt = f"""
            Rol: Experto DIAN. Genera {batch_size} preguntas técnicas de alto nivel para:
            OPEC: {opec_data['opec_number']} - {opec_data['job_title']}
            TEMAS CLAVE: Liquidación Oficial, Recursos, Vía Gubernativa, Fiscalización.
            
            Formato JSON:
            {{
                "questions": [
                    {{
                        "stem": "Caso práctico...",
                        "options": {{"A": "...", "B": "...", "C": "..."}},
                        "correct_key": "A",
                        "rationale": "Explicación técnica basada en ET...",
                        "topic": "Fiscalización 236739",
                        "track": "FUNCIONAL",
                        "difficulty": 4
                    }}
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
                candidates = data.get("questions", [])
                
                for item in candidates:
                    h = compute_hash(item.get("stem"))
                    if not db.query(Question).filter_by(hash_norm=h).first():
                        q = Question(
                            question_id=str(uuid.uuid4()),
                            track=item.get("track", "FUNCIONAL"),
                            macro_dominio="Liquidación y Fiscalización",
                            micro_competencia="Vía Gubernativa",
                            competency="Técnica",
                            topic=f"OPEC {opec_data['opec_number']}",
                            difficulty=4,
                            stem=item.get("stem"),
                            options_json=item.get("options"),
                            correct_key=item.get("correct_key"),
                            rationale=item.get("rationale"),
                            source_refs="Estatuto Tributario",
                            created_at=datetime.utcnow(),
                            hash_norm=h
                        )
                        db.add(q)
                        total_new += 1
                
                db.commit()
                
            except Exception as e:
                print(f"Error lote: {e}")
                time.sleep(1)
            
    except Exception as e:
        print(f"Error client: {e}")
    finally:
        db.close()
        print(f"✅ Generación Específica Completada: {total_new} preguntas nuevas.")

if __name__ == "__main__":
    populate_exact_opec()
