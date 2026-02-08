
import os
import sys
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

# Load env vars
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import SessionLocal
from db.models import UserOPEC, Question
from core.generators.llm import LLMGenerator

# Disable RAG by mocking NormativaManager or just passing text directly
# We will modify the generator call logic in this script to be simpler

def populate_fast():
    print("🚀 Iniciando población RÁPIDA (Sin RAG) para GESTOR III...")
    db: Session = SessionLocal()

    try:
        # 1. OPEC Data (Re-using logic to ensure it's there)
        opec_data = {
            "opec_number": "236769",
            "job_title": "GESTOR III",
            "purpose": "AT-FL-3006. DESARROLLAR INVESTIGACIONES TRIBUTARIAS...",
            "functions": [
                "HACER EL ANALISIS PRELIMINAR DE LAS DENUNCIAS DE FISCALIZACION...",
                "HACER LA PRECRITICA Y CLASIFICACION DE LOS INSUMOS...",
                "PROFERIR LOS ACTOS ADMINISTRATIVOS DE TRAMITE...",
                "REALIZAR INVESTIGACIONES PARA DETERMINAR EL CUMPLIMIENTO..."
            ]
        }
        
        # 2. Generate without RAG context to avoid freeze
        mistral_key = os.getenv("MISTRAL_API_KEY", "mo22xN9XNmdNT1QHvp7LPKmu27KvmZ13")
        
        # Manually constructing generator to override internal RAG call if needed
        # But standard generate_from_text calls NormativaManager inside try-except.
        # If it hung, it's likely the library import or initialization.
        # We will use a direct prompt approach with the client to bypass the specific method hanging.
        
        from mistralai import Mistral
        client = Mistral(api_key=mistral_key)
        
        prompt = f"""
        Actúa como Experto DIAN. Genera 5 preguntas de selección múltiple (Situacionales Tipo GOA) para:
        CARGO: {opec_data['job_title']}
        FUNCIONES: {', '.join(opec_data['functions'])}
        
        FORMATO JSON:
        {{
            "questions": [
                {{
                    "stem": "Caso situaciones...",
                    "options": {{"A": "x", "B": "y", "C": "z"}},
                    "correct_key": "A",
                    "rationale": "Justificación técnica...",
                    "topic": "Fiscalización",
                    "track": "FUNCIONAL",
                    "difficulty": 3
                }}
            ]
        }}
        """
        
        print("🤖 Enviando solicitud directa a Mistral (Bypass RAG)...")
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        import json
        content = response.choices[0].message.content
        data = json.loads(content)
        
        candidates = data.get("questions", [])
        print(f"✅ Recibidas {len(candidates)} preguntas.")
        
        saved_count = 0
        from core.dedupe import compute_hash
        
        for item in candidates:
            h = compute_hash(item.get("stem"))
            if not db.query(Question).filter_by(hash_norm=h).first():
                q = Question(
                    question_id=str(uuid.uuid4()),
                    track=item.get("track", "FUNCIONAL"),
                    macro_dominio="Fiscalización",
                    micro_competencia="Procedimiento Tributario",
                    competency="Gestión",
                    topic=f"OPEC {opec_data['opec_number']} - Flash",
                    difficulty=3,
                    stem=item.get("stem"),
                    options_json=item.get("options"),
                    correct_key=item.get("correct_key"),
                    rationale=item.get("rationale"),
                    source_refs="Mistral Fast Gen",
                    created_at=datetime.utcnow(),
                    hash_norm=h
                )
                db.add(q)
                saved_count += 1
        
        db.commit()
        print(f"🎉 Guardadas {saved_count} preguntas en modo rápido.")

    except Exception as e:
        print(f"❌ Error Fast: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_fast()
