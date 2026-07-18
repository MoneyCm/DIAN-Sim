
import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
load_dotenv()

# Import project session and engine
from db.session import SessionLocal, engine

def find_and_delete_case():
    db = SessionLocal()
    try:
        # Search for the case by title or content
        search_pattern = "%Horizonte%"
        
        print(f"🔍 Buscando casos con patrón: '{search_pattern}' en {engine.url.database}...")
        
        # 1. Find the case ID
        query = text("SELECT id, title FROM case_studies WHERE title ILIKE :pattern OR text ILIKE :pattern")
        result = db.execute(query, {"pattern": search_pattern}).fetchall()
        
        if not result:
            print("❌ No se encontró el caso con ese título o contenido.")
            # Let's list some cases to see what's there
            print("--- DEBUG: First 5 cases in DB ---")
            debug_query = text("SELECT id, title FROM case_studies LIMIT 5")
            debug_result = db.execute(debug_query).fetchall()
            for row in debug_result:
                print(f"ID: {row[0]}, Title: '{row[1]}'")
            return

        for row in result:
            case_id, title = row
            print(f"✅ Encontrado: ID={case_id}, Título='{title}'")
            
            # 2. Delete associated questions
            del_questions = text("DELETE FROM questions WHERE case_id = :case_id")
            db.execute(del_questions, {"case_id": case_id})
            print(f"🗑️ Preguntas asociadas eliminadas para el caso {case_id}.")
            
            # 3. Delete the case study
            del_case = text("DELETE FROM case_studies WHERE id = :case_id")
            db.execute(del_case, {"case_id": case_id})
            print(f"🗑️ Caso '{title}' (ID: {case_id}) eliminado.")
        
        db.commit()
        print("🚀 Operación completada con éxito.")
        
    except Exception as e:
        db.rollback()
        print(f"🔥 Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    find_and_delete_case()
