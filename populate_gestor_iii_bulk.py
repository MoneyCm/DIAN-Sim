
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

def populate_bulk(target_total=50):
    print(f"🚀 Iniciando Generación Masiva: {target_total} Preguntas para GESTOR III (Modo Rápido)...")
    db: Session = SessionLocal()
    
    total_new = 0
    batch_size = 5
    mistral_key = os.getenv("MISTRAL_API_KEY", "mo22xN9XNmdNT1QHvp7LPKmu27KvmZ13")
    
    # OPEC Data
    opec_data = {
        "opec_number": "236769",
        "job_title": "GESTOR III",
        "purpose": "AT-FL-3006. DESARROLLAR INVESTIGACIONES TRIBUTARIAS...",
        "functions": [
            "HACER EL ANALISIS PRELIMINAR DE LAS DENUNCIAS DE FISCALIZACION...",
            "HACER LA PRECRITICA Y CLASIFICACION DE LOS INSUMOS...",
            "PROFERIR LOS ACTOS ADMINISTRATIVOS DE TRAMITE...",
            "REALIZAR INVESTIGACIONES PARA DETERMINAR EL CUMPLIMIENTO...",
            "REVISAR TECNICA Y O JURIDICAMENTE LOS EXPEDIENTES..."
        ]
    }

    try:
        from mistralai import Mistral
        client = Mistral(api_key=mistral_key)
        
        iteration = 1
        while total_new < target_total:
            print(f"\n🔄 Lote {iteration} | Meta: {total_new}/{target_total}")
            
            # Rotating focus slightly could help variety, but for now we trust randomness
            prompt = f"""
            Actúa como Experto DIAN. Genera {batch_size} preguntas de selección múltiple (Situacionales Tipo GOA - Casos Prácticos) para:
            CARGO: {opec_data['job_title']}
            FUNCIONES: {', '.join(opec_data['functions'])}
            
            IMPORTANTE:
            - Deben ser casos distintos a los anteriores.
            - Nivel Profesional/Asesor.
            - Enfocadas en Procedimiento Tributario y Aduanero.
            
            FORMATO JSON:
            {{
                "questions": [
                    {{
                        "stem": "En el curso de una investigación a la empresa X...",
                        "options": {{"A": "...", "B": "...", "C": "..."}},
                        "correct_key": "A",
                        "rationale": "Según el Estatuto Tributario...",
                        "topic": "Fiscalización",
                        "track": "FUNCIONAL",
                        "difficulty": 3
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
                
                batch_saved = 0
                for item in candidates:
                    h = compute_hash(item.get("stem"))
                    # Dedupe
                    if not db.query(Question).filter_by(hash_norm=h).first():
                        q = Question(
                            question_id=str(uuid.uuid4()),
                            track=item.get("track", "FUNCIONAL"),
                            macro_dominio="Fiscalización",
                            micro_competencia="Procedimiento Tributario",
                            competency="Gestión",
                            topic=f"OPEC {opec_data['opec_number']} - Masivo",
                            difficulty=3,
                            stem=item.get("stem"),
                            options_json=item.get("options"),
                            correct_key=item.get("correct_key"),
                            rationale=item.get("rationale"),
                            source_refs="Mistral Bulk Gen",
                            created_at=datetime.utcnow(),
                            hash_norm=h
                        )
                        db.add(q)
                        batch_saved += 1
                
                db.commit()
                total_new += batch_saved
                print(f"   ✅ Guardadas en este lote: {batch_saved}")
                
                if batch_saved == 0:
                    print("   ⚠️ Lote duplicado completo, reintentando...")
                
            except Exception as e:
                print(f"   ❌ Error lote: {e}")
                time.sleep(2)
            
            iteration += 1
            if total_new < target_total:
                time.sleep(1) # Polite rate limit
                
    except Exception as e:
        print(f"❌ Error General: {e}")
    finally:
        db.close()
        print(f"\n🎉 FINALIZADO. Total nuevas preguntas: {total_new}")

if __name__ == "__main__":
    populate_bulk(100)
