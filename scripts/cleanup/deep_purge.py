
import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
from db.session import SessionLocal

def final_deep_search():
    db = SessionLocal()
    try:
        # 1. Buscar el ID del caso que contenga el código del contrato LPN-2023-054
        query = text("SELECT id, title, text FROM case_studies WHERE text LIKE '%LPN-2023-054%' OR title LIKE '%LPN-2023-054%'")
        cases = db.execute(query).fetchall()
        
        if cases:
            print(f"🚩 ¡ENCONTRADO EN NEON! {len(cases)} casos encontrados.")
            for c in cases:
                print(f"ID: {c[0]}, Title: '{c[1]}'")
                # Eliminar de Neon
                db.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": c[0]})
                db.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": c[0]})
                print(f"🗑️ Eliminado Caso {c[0]} y sus preguntas de Neon.")
            db.commit()
            print("🚀 Borrado de Neon completado.")
        else:
            print("✅ No hay rastro de 'LPN-2023-054' en Neon.")

        # 2. Buscar si hay preguntas sueltas que lo mencionen
        q_query = text("SELECT question_id FROM questions WHERE stem LIKE '%LPN-2023-054%'")
        qs = db.execute(q_query).fetchall()
        if qs:
            print(f"🚩 ¡ENCONTRADO EN NEON! {len(qs)} preguntas sueltas.")
            db.execute(text("DELETE FROM questions WHERE stem LIKE '%LPN-2023-054%'"))
            db.commit()
            print("🗑️ Preguntas sueltas eliminadas de Neon.")

    finally:
        db.close()

if __name__ == "__main__":
    final_deep_search()
