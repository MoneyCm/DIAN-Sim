import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- 🔍 BUSCANDO PREGUNTAS CON ENTIDAD ERRÓNEA (CNSC) ---")
        
        # Buscar en preguntas
        q_search = conn.execute(text("""
            SELECT question_id, LEFT(stem, 100) 
            FROM questions 
            WHERE (stem ILIKE '%Comisión Nacional del Servicio Civil%' 
               OR stem ILIKE '%CNSC%')
               AND topic LIKE '%236769%'
        """))
        q_rows = q_search.fetchall()
        print(f"Preguntas afectadas: {len(q_rows)}")
        for r in q_rows:
            print(f"- ID: {r[0]} | Preview: {r[1]}...")

        # Buscar en casos
        c_search = conn.execute(text("""
            SELECT id, title 
            FROM case_studies 
            WHERE (text ILIKE '%Comisión Nacional del Servicio Civil%' 
               OR text ILIKE '%CNSC%'
               OR title ILIKE '%Comisión Nacional del Servicio Civil%'
               OR title ILIKE '%CNSC%')
               AND topic LIKE '%236769%'
        """))
        c_rows = c_search.fetchall()
        print(f"\nCasos afectados: {len(c_rows)}")
        for r in c_rows:
            print(f"- ID: {r[0]} | Título: {r[1]}")

except Exception as e:
    print(f"Error: {e}")
