from db.session import SessionLocal
from db.models import Question

def check_progress():
    db = SessionLocal()
    try:
        sources = ["IA (Gemini) - OPEC 236739", "IA (Mistral) - OPEC 236739"]
        total_batch = 0
        for diff in [1, 2, 3]:
            count = db.query(Question).filter(
                Question.source_refs.in_(sources),
                Question.difficulty == diff
            ).count()
            print(f"Dificultad {diff}: {count} preguntas")
            total_batch += count
        print(f"Total Generado en este lote: {total_batch}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_progress()
