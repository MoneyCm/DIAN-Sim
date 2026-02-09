
import sys
import os
from sqlalchemy import func

# Add project root to path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from db.models import Question

def analyze():
    db = SessionLocal()
    
    print("--- 📊 ANÁLISIS DEL BANCO DE PREGUNTAS ---")
    
    # 1. Total
    total = db.query(Question).count()
    print(f"\n🔢 TOTAL PREGUNTAS: {total}")
    
    # 2. Por Track (Eje)
    print("\n--- POR EJE (TRACK) ---")
    by_track = db.query(Question.track, func.count(Question.question_id)).group_by(Question.track).all()
    for track, count in by_track:
        print(f"   - {track}: {count}")
        
    # 3. Por Tema (Top 20) -> Para ver "OPECs"
    print("\n--- POR TEMA (TOP 20) ---")
    by_topic = db.query(Question.topic, func.count(Question.question_id)).group_by(Question.topic).order_by(func.count(Question.question_id).desc()).limit(20).all()
    
    for topic, count in by_topic:
        print(f"   - {topic}: {count}")

    # 4. Buscando Patrones de OPEC (Gestor, etc)
    print("\n--- AGRUPACIÓN INTELIGENTE (Por Job Title detectado) ---")
    all_topics = db.query(Question.topic).distinct().all()
    
    opec_map = {}
    for (t,) in all_topics:
        # Simple heuristic: Split by " - " or take first 15 chars
        if not t: continue
        
        # Detect "Gestor X"
        key = "General"
        t_upper = t.upper()
        
        if "GESTOR" in t_upper:
            # Extract "GESTOR I", "GESTOR II", etc.
            import re
            m = re.search(r'(GESTOR\s+[IV]+)', t_upper)
            if m:
                key = m.group(1)
            else:
                key = "GESTOR (Otro)"
        elif "OPEC" in t_upper:
             m = re.search(r'(OPEC\s+\d+)', t_upper)
             if m:
                 key = m.group(1)
             else:
                 key = "OPEC (Otro)"
        else:
            # Fallback to broader category if possible, or just "Otros"
            key = "Otros Temas"

        opec_map[key] = opec_map.get(key, 0) + db.query(Question).filter(Question.topic == t).count()
        
    for k, v in opec_map.items():
        print(f"   - {k}: {v}")

    db.close()

if __name__ == "__main__":
    analyze()
