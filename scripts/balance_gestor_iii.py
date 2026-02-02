
import os
import sys
import time
import json
import uuid
from dotenv import load_dotenv
from sqlalchemy import and_
from sqlalchemy.orm import Session
from datetime import datetime

# Load env vars
load_dotenv()

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from db.models import Question
from core.profiles import PROFILES
from core.dedupe import compute_hash

# TARGET: How many questions per (Topic + Difficulty) bucket?
# 16 Topics * 3 Difficulties = 48 Buckets. 
# Target 25 per bucket => ~1,200 Total Questions.
TARGET_PER_BUCKET = 25 

def get_current_count(db, topic, difficulty):
    return db.query(Question).filter(
        and_(
            Question.topic.ilike(f"%{topic}%"),
            Question.difficulty == difficulty
        )
    ).count()

def generate_bucket(client, topic, difficulty, count, track_type):
    if count <= 0: return []
    
    print(f"   ⚡ Generando {count} preguntas para [{topic}] (Dif: {difficulty})...")
    
    prompt = f"""
    Actúa como Experto DIAN. Genera EXACTAMENTE {count} preguntas de selección múltiple sobre:
    TEMA: {topic}
    DIFICULTAD: {difficulty} (1=Básico, 2=Intermedio, 3=Avanzado)
    TIPO: {track_type}
    
    CONTEXTO: Perfil Gestor III (Fiscalización y Evasión).
    
    REQUISITOS:
    1. Formato JSON (array "questions").
    2. Casos prácticos cortos (Situacionales).
    3. 3 Opciones de respuesta (A, B, C).
    4. Cita normativa real en 'rationale'.
    
    JSON:
    {{
      "questions": [
        {{
          "stem": "Caso...",
          "options": {{"A": "..", "B": "..", "C": ".."}},
          "correct_key": "A",
          "rationale": "Art X Estatuto...",
          "topic": "{topic}",
          "track": "{track_type}",
          "difficulty": {difficulty}
        }}
      ]
    }}
    """
    
    retries = 3
    for attempt in range(retries):
        try:
            response = client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return data.get("questions", [])
        except Exception as e:
            print(f"      ⚠️ Error intento {attempt+1}: {e}")
            time.sleep(2)
            
    return []

def balance_bank():
    print(f"⚖️ Iniciando Balanceo Inteligente (Meta: {TARGET_PER_BUCKET} por bucket)...")
    
    key = os.getenv("MISTRAL_API_KEY", "mo22xN9XNmdNT1QHvp7LPKmu27KvmZ13")
    if not key:
        print("❌ Sin API Key de Mistral")
        return

    try:
        from mistralai import Mistral
        client = Mistral(api_key=key)
        
        target_profile = PROFILES["Gestor III (OPEC 236769)"]
        db = SessionLocal()
        
        # Build Requirements
        buckets = []
        
        # Functional
        for track, topics in target_profile["functional_tracks"].items():
            for t in topics:
                for d in [1, 2, 3]:
                    buckets.append({"topic": t, "diff": d, "type": track})
                    
        # Behavioral
        for c in target_profile["behavioral_competencies"]:
            for d in [1, 2, 3]:
                buckets.append({"topic": c, "diff": d, "type": "COMPORTAMENTAL"})
                
        total_generated = 0
        
        for b in buckets:
            current = get_current_count(db, b["topic"], b["diff"])
            needed = TARGET_PER_BUCKET - current
            
            if needed > 0:
                print(f"🛑 Brecha detectada: {b['topic']} | Dif {b['diff']} | Faltan {needed}")
                
                new_qs = generate_bucket(client, b["topic"], b["diff"], needed, b["type"])
                
                saved_in_bucket = 0
                for item in new_qs:
                    h = compute_hash(item.get("stem"))
                    if not db.query(Question).filter_by(hash_norm=h).first():
                        q = Question(
                            question_id=str(uuid.uuid4()),
                            track=item.get("track", b["type"]),
                            macro_dominio=b["topic"], 
                            micro_competencia=b["type"],
                            competency=b["topic"],
                            topic=b["topic"],
                            difficulty=b["diff"],
                            stem=item.get("stem"),
                            options_json=item.get("options"),
                            correct_key=item.get("correct_key"),
                            rationale=item.get("rationale"),
                            source_refs="Auto-Balancer v1",
                            created_at=datetime.utcnow(),
                            hash_norm=h
                        )
                        db.add(q)
                        saved_in_bucket += 1
                        
                db.commit()
                total_generated += saved_in_bucket
                print(f"   ✅ Guardadas: {saved_in_bucket} (Total Sesión: {total_generated})")
                time.sleep(1) 
            else:
                pass 
                
        print(f"\n✨ BALANCEO COMPLETADO. Se agregaron {total_generated} preguntas nuevas.")
        db.close()
        
    except Exception as general_e:
        print(f"❌ Error Critical: {general_e}")

if __name__ == "__main__":
    balance_bank()
