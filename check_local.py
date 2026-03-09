
import os
import sys
from sqlalchemy import create_engine, text

db_path = os.path.abspath("dian_sim.db")
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL)

def check_local_db():
    try:
        with engine.connect() as conn:
            print(f"🔌 Conectado a base local: {db_path}")
            
            keywords = [
                '%LPN-2023-054%',
                '%San Vicente%',
                '%Constructora Horizonte%',
                '%Fiscalización de Irregularidades%'
            ]
            
            found = False
            for kw in keywords:
                cases = conn.execute(text("SELECT id, title FROM case_studies WHERE title LIKE :kw OR text LIKE :kw"), {"kw": kw}).fetchall()
                if cases:
                    found = True
                    for c in cases:
                        print(f"⚠️ Encontrado en SQLite local (case_studies) por '{kw}': ID={c[0]}, Title={c[1]}")
                        
                        # Eliminar caso de SQLite
                        conn.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": c[0]})
                        conn.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": c[0]})
                        print(f"🗑️ Eliminado de la base local.")
            
            if found:
                conn.commit()
            else:
                print("✅ No hay rastro en la base local SQLite.")
                
    except Exception as e:
        print(f"🔥 Error leyendo local: {e}")

if __name__ == "__main__":
    check_local_db()
