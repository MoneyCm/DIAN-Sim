
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
from db.models import Question
from core.profiles import PROFILES
from core.dedupe import compute_hash

def force_generation_1k():
    # Prepare Topic Pool FIRST to count correctly
    p = PROFILES["Gestor III (OPEC 236769)"]
    topics = []
    topics.extend(p["functional_tracks"]["FUNCIONAL"])
    topics.extend(p["functional_tracks"]["INTEGRIDAD"])
    topics.extend(p["behavioral_competencies"])
    
    db = SessionLocal()
    # Filter by topics belonging to this profile
    current_count = db.query(Question).filter(Question.topic.in_(topics)).count()
    
    TARGET_TOTAL = 1000
    TARGET_NEW = TARGET_TOTAL - current_count
    
    print(f"📊 Estado Actual (Gestor III): {current_count} preguntas.")
    
    if TARGET_NEW <= 0:
        print(f"✅ ¡META DE 1000 ALCANZADA para Gestor III! (Hay {current_count})")
        return

    BATCH_SIZE = 5
    
    print(f"🚀 INICIANDO MODALIDAD 'FUERZA BRUTA': META {TARGET_NEW} NUEVAS PREGUNTAS (Gestor III)")
    
    key = os.getenv("MISTRAL_API_KEY", "mo22xN9XNmdNT1QHvp7LPKmu27KvmZ13")
    if not key:
        print("❌ Sin API Key")
        return

    try:
        from mistralai import Mistral
        client = Mistral(api_key=key)
        
        print(f"📋 Pool de Temas: {len(topics)} temas activos.")
        
        total_added = 0
        total_attempts = 0
        
        while total_added < TARGET_NEW:
            # Random selection for variety
            topic = random.choice(topics)
            difficulty = random.choice([1, 2, 3])
            
            # Decide track based on topic membership
            track = "FUNCIONAL"
            if topic in p["functional_tracks"]["INTEGRIDAD"]: track = "INTEGRIDAD"
            if topic in p["behavioral_competencies"]: track = "COMPORTAMENTAL"
            
            # PROMPT
            prompt = f"""
            Actúa como Experto DIAN. Genera {BATCH_SIZE} preguntas de selección múltiple (Situacionales - Casos Cortos).
            PERFIL: Gestro III (OPEC 236769) - Fiscalización y Evasión.
            TEMA: {topic}
            DIFICULTAD: {difficulty} (1-3)
            
            FORMATO JSON ÚNICO:
            {{
                "questions": [
                    {{
                        "stem": "Planteamiento del caso...",
                        "options": {{"A": "...", "B": "...", "C": "..."}},
                        "correct_key": "A",
                        "rationale": "Justificación normativa...",
                        "topic": "{topic}",
                        "difficulty": {difficulty}
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
                
                batch_count = 0
                for item in candidates:
                    h = compute_hash(item.get("stem"))
                    if not db.query(Question).filter_by(hash_norm=h).first():
                        q = Question(
                            question_id=str(uuid.uuid4()),
                            track=track,
                            macro_dominio=topic,
                            micro_competencia=track,
                            competency=topic,
                            topic=topic,
                            difficulty=difficulty,
                            stem=item.get("stem"),
                            options_json=item.get("options"),
                            correct_key=item.get("correct_key"),
                            rationale=item.get("rationale"),
                            source_refs=f"Brute Force Gen {datetime.now().strftime('%H:%M')}",
                            created_at=datetime.utcnow(),
                            is_verified=False,
                            hash_norm=h
                        )
                        db.add(q)
                        batch_count += 1
                
                db.commit()
                total_added += batch_count
                total_attempts += 1
                
                print(f"📦 Lote {total_attempts}: +{batch_count} guardadas ({topic} D{difficulty}). Total Acumulado: {total_added}/{TARGET_NEW}")
                
                # Dynamic sleep to respect rate limits gently
                time.sleep(1.5)
                
            except Exception as e:
                print(f"⚠️ Error en lote: {e}")
                time.sleep(3)
        
        print("\n🏆 META ALCANZADA.")
        db.close()
            
    except Exception as e:
        print(f"❌ Error Fatal: {e}")

if __name__ == "__main__":
    force_generation_1k()
