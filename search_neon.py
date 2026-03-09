
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

def search_and_destroy():
    try:
        with engine.connect() as conn:
            print(f"🔌 Conectado a: {engine.url.database} en {engine.url.host}")
            
            # Palabras clave muy específicas del caso
            keywords = [
                '%LPN-2023-054%',
                '%San Vicente%',
                '%Constructora Horizonte%',
                '%Fiscalización de Irregularidades%'
            ]
            
            case_ids_to_delete = set()
            
            for kw in keywords:
                # Buscar en case_studies (título y texto)
                cases = conn.execute(text("""
                    SELECT id, title FROM case_studies 
                    WHERE title ILIKE :kw OR text ILIKE :kw
                """), {"kw": kw}).fetchall()
                
                for c in cases:
                    print(f"🔍 Encontrado en case_studies por '{kw}': ID={c[0]}, Title={c[1]}")
                    case_ids_to_delete.add(c[0])
                
                # Buscar en questions (stem y rationale) por si están huérfanas
                qs = conn.execute(text("""
                    SELECT question_id, case_id FROM questions 
                    WHERE stem ILIKE :kw OR rationale ILIKE :kw
                """), {"kw": kw}).fetchall()
                
                for q in qs:
                    print(f"🔍 Encontrado en questions por '{kw}': Q_ID={q[0]}, Case_ID={q[1]}")
                    if q[1]:
                        case_ids_to_delete.add(q[1])

            if not case_ids_to_delete:
                print("✅ No se encontraron rastros de este caso en la base de datos de Neon.")
                return

            print(f"\n🗑️ Eliminando {len(case_ids_to_delete)} casos y sus preguntas...")
            for cid in case_ids_to_delete:
                # Borrar preguntas primero
                q_del = conn.execute(text("DELETE FROM questions WHERE case_id = :cid"), {"cid": cid})
                # Borrar caso
                c_del = conn.execute(text("DELETE FROM case_studies WHERE id = :cid"), {"cid": cid})
                print(f"  -> Caso {cid}: Eliminadas {q_del.rowcount} preguntas y {c_del.rowcount} caso(s).")
            
            conn.commit()
            print("🚀 Limpieza completada exitosamente.")

    except Exception as e:
        print(f"🔥 Error: {e}")

if __name__ == "__main__":
    search_and_destroy()
