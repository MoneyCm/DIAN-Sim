import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

terms = ["Horizonte", "San Vicente", "LPN-2023-054", "Soluciones SAS"]

try:
    with engine.connect() as conn:
        print("--- 🔍 BUSCANDO EN NEON (FRAGMENTOS) ---")
        for term in terms:
            # Buscar en case_studies
            res = conn.execute(text(f"SELECT id, title FROM case_studies WHERE title ILIKE :t OR text ILIKE :t"), {"t": f"%{term}%"}).fetchall()
            for r in res:
                print(f"📍 NEON CASE FOUND: ID={r[0]} | Title={r[1]}")
                # Killem
                conn.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": r[0]})
                conn.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": r[0]})
                print("🗑️ Deleted.")

            # Buscar en questions sueltas
            res_q = conn.execute(text(f"SELECT question_id, LEFT(stem, 50) FROM questions WHERE stem ILIKE :t"), {"t": f"%{term}%"}).fetchall()
            for r in res_q:
                print(f"📍 NEON QUESTION FOUND: ID={r[0]} | Stem={r[1]}...")
                conn.execute(text("DELETE FROM questions WHERE question_id = :id"), {"id": r[0]})
                print("🗑️ Deleted.")
        conn.commit()
    print("✅ Neon Purge finished.")
except Exception as e:
    print(f"Error Neon: {e}")
