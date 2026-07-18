import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- 🔍 BUSCANDO CASO ESPECÍFICO 'SOLUCIONES SAS' ---")
        # Buscar por fragmento del título o texto
        res = conn.execute(text("""
            SELECT id, title FROM case_studies 
            WHERE title ILIKE '%Soluciones SAS%' 
               OR text ILIKE '%Soluciones SAS%'
               OR text ILIKE '%Villaflores%'
        """)).fetchall()
        
        if not res:
            print("No se encontró el caso en Neon con esos términos.")
        else:
            for row in res:
                print(f"ENCONTRADO: ID={row.id}, Título={row.title}")
                # Eliminar preguntas
                q_del = conn.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": row.id}).rowcount
                # Eliminar caso
                c_del = conn.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": row.id}).rowcount
                print(f"Eliminadas {q_del} preguntas y el caso.")
        
        conn.commit()
        print("✅ Operación completada.")

except Exception as e:
    print(f"Error: {e}")
