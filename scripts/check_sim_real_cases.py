import os
import sys
import unicodedata
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from db.session import SessionLocal
from db.models import CaseStudy, Question

BANNED_SIM_REAL_TERMS = [
    "comision nacional del servicio civil", "cnsc", "constructora horizonte",
    "constructora soluciones sas", "alcaldia municipal", "alcalde de villaflores",
    "villaflores", "san vicente", "lpn-2023-054", "contratacion publica",
    "obra publica", "licitacion publica", "ley 80 de 1993", "centro de salud de tercer nivel",
    "procuraduria", "fiscalia", "dumping", "sobornos", "campana electoral",
    "sipr", "horizonte s.a.", "horizonte sa", "lpn 2023"
]

def _normalize_exam_text(value):
    value = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch))

def _case_is_valid_for_dian(case):
    questions = case.questions or []
    if not questions:
        return False, "Sin preguntas"
        
    haystack_parts = [case.title, case.text, case.topic]
    for question in questions:
        haystack_parts.extend([
            question.stem,
            question.rationale,
            question.topic,
            question.competency,
        ])

        # Verificar opciones
        import json
        try:
            opts = question.options_json if isinstance(question.options_json, dict) else json.loads(question.options_json)
        except Exception as e:
            return False, f"Error cargando opciones: {e}"
            
        if len(opts) != 3:
            return False, f"Pregunta {question.question_id} tiene {len(opts)} opciones (requiere exactamente 3)"

    haystack = " ".join(_normalize_exam_text(part) for part in haystack_parts if part)
    if not haystack:
        return False, "Sin texto para indexar"

    # Verificar términos prohibidos
    for term in BANNED_SIM_REAL_TERMS:
        if term in haystack:
            return False, f"Contiene término prohibido: {term}"

    # Verificar palabra clave DIAN
    if "dian" not in haystack:
        return False, "No contiene la palabra 'dian'"

    return True, "VÁLIDO"

def main():
    print("🔎 INICIANDO AUDITORÍA DE CASOS PROTAGÓNICOS EN NEON...")
    db = SessionLocal()
    try:
        cases = db.query(CaseStudy).all()
        print(f"Total de casos en la base de datos: {len(cases)}")
        
        valid_cases = []
        invalid_cases = []
        
        for c in cases:
            is_valid, reason = _case_is_valid_for_dian(c)
            # Contar preguntas por dificultad
            diffs = {}
            for q in c.questions:
                diffs[q.difficulty] = diffs.get(q.difficulty, 0) + 1
                
            info = {
                "id": c.id,
                "title": c.title[:50],
                "topic": c.topic,
                "questions_count": len(c.questions),
                "diff_breakdown": diffs,
                "reason": reason
            }
            if is_valid:
                valid_cases.append(info)
            else:
                invalid_cases.append(info)
                
        print(f"\n✅ CASOS VÁLIDOS ({len(valid_cases)}):")
        for vc in valid_cases:
            print(f" - [{vc['id']}] {vc['title']} | Topic: {vc['topic']} | Diffs: {vc['diff_breakdown']}")
            
        print(f"\n❌ CASOS INVÁLIDOS ({len(invalid_cases)}):")
        for ic in invalid_cases:
            print(f" - [{ic['id']}] {ic['title']} | Razón: {ic['reason']} | Topic: {ic['topic']}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
