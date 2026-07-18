import os
import sqlite3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def nuclear_purge(name, engine_or_conn):
    print(f"\n--- 🔥 NUCLEAR PURGE: {name} ---")
    query_cases = "DELETE FROM case_studies WHERE title LIKE '%Horizonte%' OR text LIKE '%Horizonte%' OR text LIKE '%CNSC%' OR text LIKE '%Comisión Nacional%'"
    query_qs = "DELETE FROM questions WHERE stem LIKE '%Horizonte%' OR stem LIKE '%CNSC%' OR stem LIKE '%Comisión Nacional%'"
    
    try:
        if name == "NEON":
            with engine_or_conn.connect() as conn:
                r1 = conn.execute(text(query_cases))
                r2 = conn.execute(text(query_qs))
                conn.commit()
                print(f"Neon: {r1.rowcount} casos y {r2.rowcount} preguntas eliminados.")
        else:
            cur = engine_or_conn.cursor()
            # SQLite handles % differently in direct SQL vs params, doing it safe
            cur.execute("DELETE FROM case_studies WHERE title LIKE '%Horizonte%' OR text LIKE '%Horizonte%' OR text LIKE '%CNSC%' OR text LIKE '%Comisión Nacional%'")
            c1 = cur.rowcount
            cur.execute("DELETE FROM questions WHERE stem LIKE '%Horizonte%' OR stem LIKE '%CNSC%' OR stem LIKE '%Comisión Nacional%'")
            c2 = cur.rowcount
            engine_or_conn.commit()
            print(f"SQLite: {c1} casos y {c2} preguntas eliminados.")
    except Exception as e:
        print(f"Error {name}: {e}")

# Neon
url = os.getenv("DATABASE_URL")
if url: nuclear_purge("NEON", create_engine(url))

# SQLite
db_path = "dian_sim.db"
if os.path.exists(db_path): nuclear_purge("SQLITE", sqlite3.connect(db_path))

print("✅ Purga nuclear finalizada.")
