import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- 📊 ESTADO ACTUAL DE CASOS DE ESTUDIO EN NEON ---")
        res = conn.execute(text("SELECT title, topic, difficulty FROM case_studies ORDER BY created_at DESC"))
        rows = res.fetchall()
        print(f"Total de casos: {len(rows)}")
        for r in rows:
            print(f"- Título: {r[0]} | Topic: {r[1]} | Diff: {r[2]}")
            
except Exception as e:
    print(f"Error: {e}")
