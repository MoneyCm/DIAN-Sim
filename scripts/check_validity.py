import sys
import os
import datetime

# Add root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import SessionLocal
from db.models import Question

def check_obsolescence():
    """Scans the database for potential outdated questions."""
    db = SessionLocal()
    questions = db.query(Question).all()
    
    # Blacklist of terms that suggest the question is old
    # e.g. Old UVT values, specific years, repealed laws
    blacklist = [
        "año gravable 2020",
        "año gravable 2021",
        "UVT de $38.004", # 2022
        "UVT de $42.412", # 2023
        "Ley 1943", # Financiamiento (inexequible)
        "Decreto 568 de 2020", # Emergencia COVID (temporal)
    ]
    
    print(f"🔍 [AUDITOR] Iniciando escaneo de {len(questions)} preguntas...")
    print(f"📅 Fecha de Auditoría: {datetime.date.today()}")
    print("-" * 50)
    
    flagged_count = 0
    
    for q in questions:
        text_content = ((q.stem or "") + " " + (q.rationale or "") + " " + str(q.options_json or "")).lower()
        
        found_terms = []
        for term in blacklist:
            if term.lower() in text_content:
                found_terms.append(term)
        
        if found_terms:
            flagged_count += 1
            print(f"⚠️ [FLAGGED] QID: {q.question_id[:8]}...")
            print(f"   Tema: {q.topic}")
            print(f"   Términos sospechosos: {', '.join(found_terms)}")
            print("-" * 30)
            
            # Here we could auto-tag the question as "NEEDS_REVIEW" in a future update
            
    print(f"\n📊 RESUMEN:")
    print(f"Total escaneado: {len(questions)}")
    print(f"Preguntas marcadas como OBSOLETAS/RIESGO: {flagged_count}")
    
    if flagged_count == 0:
        print("✅ Todo parece estar actualizado (según lista negra actual).")
    
    db.close()

if __name__ == "__main__":
    check_obsolescence()
