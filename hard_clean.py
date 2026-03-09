import os
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# --- REGLA DE BÚSQUEDA ---
BANNED_WORDS = ["Horizonte", "Comisión Nacional", "CNSC", "San Vicente", "LPN-2023-054", "Villaflores", "Horizonte S.A."]

def clean_database(name, engine_or_conn):
    print(f"\n--- 🧹 LIMPIEZA PROFUNDA: {name} ---")
    deleted_cases = 0
    deleted_questions = 0
    
    try:
        if name == "NEON":
            with engine_or_conn.connect() as conn:
                # 1. Casos
                res = conn.execute(text("SELECT id, title, text FROM case_studies")).fetchall()
                for r in res:
                    case_id, title, content = r
                    found = False
                    for word in BANNED_WORDS:
                        if (title and word in title) or (content and word in content):
                            found = True
                            break
                    if found:
                        print(f"🗑️ Eliminando Caso en NEON: {title}")
                        conn.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": case_id})
                        conn.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": case_id})
                        deleted_cases += 1
                
                # 2. Preguntas sueltas
                res_q = conn.execute(text("SELECT question_id, stem FROM questions")).fetchall()
                for r in res_q:
                    q_id, stem = r
                    found = False
                    for word in BANNED_WORDS:
                        if stem and word in stem:
                            found = True
                            break
                    if found:
                        print(f"🗑️ Eliminando Pregunta en NEON: {q_id}")
                        conn.execute(text("DELETE FROM questions WHERE question_id = :id"), {"id": q_id})
                        deleted_questions += 1
                conn.commit()
        else:
            # SQLite
            cur = engine_or_conn.cursor()
            # 1. Casos
            cur.execute("SELECT id, title, text FROM case_studies")
            res = cur.fetchall()
            for r in res:
                case_id, title, content = r
                found = False
                for word in BANNED_WORDS:
                    if (title and word in title) or (content and word in content):
                        found = True
                        break
                if found:
                    print(f"🗑️ Eliminando Caso en SQLITE: {title}")
                    cur.execute("DELETE FROM questions WHERE case_id = ?", (case_id,))
                    cur.execute("DELETE FROM case_studies WHERE id = ?", (case_id,))
                    deleted_cases += 1
            
            # 2. Preguntas sueltas
            cur.execute("SELECT question_id, stem FROM questions")
            res_q = cur.fetchall()
            for r in res_q:
                q_id, stem = r
                found = False
                for word in BANNED_WORDS:
                    if stem and word in stem:
                        found = True
                        break
                if found:
                    print(f"🗑️ Eliminando Pregunta en SQLITE: {q_id}")
                    cur.execute("DELETE FROM questions WHERE question_id = ?", (q_id,))
                    deleted_questions += 1
            engine_or_conn.commit()
            
    except Exception as e:
        print(f"❌ Error en {name}: {e}")
    
    print(f"Resultado {name}: {deleted_cases} casos y {deleted_questions} preguntas eliminados.")

# Neon
url = os.getenv("DATABASE_URL")
if url:
    clean_database("NEON", create_engine(url))

# SQLite
db_path = "dian_sim.db"
if os.path.exists(db_path):
    clean_database("SQLITE", sqlite3.connect(db_path))

print("\n--- ✅ PROCESO DE LIMPIEZA FINALIZADO ---")
