
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configuración de rutas y carga de variables
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Forzar el uso de psycopg2 si es necesario
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def atomic_purge():
    session = SessionLocal()
    try:
        print(f"🚀 INICIANDO PURGA ATÓMICA EN NEON...")
        
        # Palabras clave del caso reportado
        banned_terms = ['%Horizonte%', '%San Vicente%', '%LPN-2023-054%', '%Constructora%']
        
        total_cases_deleted = 0
        total_questions_deleted = 0

        for term in banned_terms:
            # 1. Identificar IDs de casos que coincidan con el término en cualquier parte del texto o título
            find_cases_query = text("""
                SELECT id FROM case_studies 
                WHERE title ILIKE :term OR text ILIKE :term
            """)
            case_ids = [row[0] for row in session.execute(find_cases_query, {"term": term}).fetchall()]
            
            if case_ids:
                print(f"📍 Encontrados {len(case_ids)} casos con el término '{term}'")
                # Borrar preguntas asociadas
                del_qs = session.execute(text("DELETE FROM questions WHERE case_id IN :ids"), {"ids": tuple(case_ids)})
                total_questions_deleted += del_qs.rowcount
                # Borrar los casos
                del_cs = session.execute(text("DELETE FROM case_studies WHERE id IN :ids"), {"ids": tuple(case_ids)})
                total_cases_deleted += del_cs.rowcount

            # 2. Buscar preguntas que contengan el término pero no estén vinculadas a esos casos (huérfanas)
            del_orphans = session.execute(text("""
                DELETE FROM questions 
                WHERE stem ILIKE :term OR rationale ILIKE :term
            """), {"term": term})
            total_questions_deleted += del_orphans.rowcount

        session.commit()
        print(f"✨ RESULTADOS DE LA PURGA:")
        print(f"   - Casos eliminados: {total_cases_deleted}")
        print(f"   - Preguntas eliminadas: {total_questions_deleted}")
        
        # VERIFICACIÓN FINAL: ¿Queda algo?
        check = session.execute(text("SELECT COUNT(*) FROM case_studies WHERE title ILIKE '%Horizonte%'")).scalar()
        if check == 0:
            print("✅ Verificación exitosa: No quedan registros de 'Horizonte' en Neon.")
        else:
            print(f"⚠️ Alerta: Aún quedan {check} registros. Revisando integridad...")

    except Exception as e:
        session.rollback()
        print(f"🔥 Error crítico durante la purga: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    atomic_purge()
