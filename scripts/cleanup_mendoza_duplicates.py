import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from db.session import SessionLocal, engine

def cleanup_mendoza_duplicates():
    print("🚀 INICIANDO DEPURACIÓN DE CASOS REPETITIVOS DE CARLOS MENDOZA (ADUANAS)...")
    db = SessionLocal()
    try:
        # 1. Buscar todos los casos con el título repetitivo de aduanas
        search_pattern = "%Optimización%Fiscalización%Impor%"
        query = text("""
            SELECT id, title 
            FROM case_studies 
            WHERE title ILIKE :pattern
            ORDER BY id
        """)
        
        results = db.execute(query, {"pattern": search_pattern}).fetchall()
        total_found = len(results)
        print(f"🔍 Se encontraron {total_found} casos repetitivos de aduanas en la base de datos.")
        
        if total_found <= 2:
            print("✅ La cantidad de casos repetitivos es 2 o menos. No se requiere limpieza adicional.")
            return

        # Conservar solo los primeros 2 casos y eliminar el resto
        cases_to_keep = results[:2]
        cases_to_delete = results[2:]
        
        print(f"⭐ Casos conservados para mantener variedad aduanera (2):")
        for ck in cases_to_keep:
            print(f"   - [ID: {ck.id}] {ck.title}")
            
        print(f"\n🗑️ Eliminando {len(cases_to_delete)} casos duplicados y sus preguntas...")
        
        deleted_count = 0
        for cd in cases_to_delete:
            case_id = cd.id
            title = cd.title
            
            # A. Eliminar intentos asociados a las preguntas del caso (para evitar violación de FK)
            # Primero buscamos las preguntas del caso
            q_query = text("SELECT question_id FROM questions WHERE case_id = :case_id")
            q_ids = [row[0] for row in db.execute(q_query, {"case_id": case_id}).fetchall()]
            
            if q_ids:
                # Eliminar en question_performance
                db.execute(text("DELETE FROM question_performance WHERE question_id IN :q_ids"), {"q_ids": tuple(q_ids)})
                # Eliminar en attempts
                db.execute(text("DELETE FROM attempts WHERE question_id IN :q_ids"), {"q_ids": tuple(q_ids)})
                
            # B. Eliminar preguntas del caso
            db.execute(text("DELETE FROM questions WHERE case_id = :case_id"), {"case_id": case_id})
            
            # C. Eliminar el caso
            db.execute(text("DELETE FROM case_studies WHERE id = :case_id"), {"case_id": case_id})
            deleted_count += 1
            
        db.commit()
        print(f"\n✅ ¡Limpieza completada! Se eliminaron {deleted_count} casos duplicados y sus respectivas preguntas de forma segura.")
        
    except Exception as e:
        db.rollback()
        print(f"🔥 Error en la limpieza: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_mendoza_duplicates()
