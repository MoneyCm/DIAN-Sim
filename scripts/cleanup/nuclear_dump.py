import os
import sqlite3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def dump_titles(name, engine_or_conn):
    print(f"\n--- 📋 VOLCADO DE TÍTULOS: {name} ---")
    try:
        if name == "NEON":
            with engine_or_conn.connect() as conn:
                res = conn.execute(text("SELECT id, title FROM case_studies"))
                rows = res.fetchall()
        else:
            cur = engine_or_conn.cursor()
            cur.execute("SELECT id, title FROM case_studies")
            rows = cur.fetchall()
            
        if not rows:
            print("V vacío.")
        for r in rows:
            print(f"ID: {r[0]} | TÍTULO: {r[1]}")
    except Exception as e:
        print(f"Error {name}: {e}")

# Neon
url = os.getenv("DATABASE_URL")
if url:
    dump_titles("NEON", create_engine(url))

# SQLite
db_path = "dian_sim.db"
if os.path.exists(db_path):
    dump_titles("SQLITE", sqlite3.connect(db_path))

# Check for other .db files
print("\n--- 🔎 BUSCANDO OTROS ARCHIVOS .db ---")
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".db") and file != "dian_sim.db":
            print(f"Encontrado: {os.path.join(root, file)}")
