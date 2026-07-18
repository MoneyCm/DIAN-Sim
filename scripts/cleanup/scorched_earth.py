
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)

def scorched_earth_purge():
    try:
        with engine.connect() as conn:
            print("--- 🔥 OPERACIÓN TIERRA QUEMADA EN NEON ---")
            
            # 1. Obtener TODOS los casos para inspección manual por script
            res = conn.execute(text("SELECT id, title, text FROM case_studies")).fetchall()
            print(f"Total de casos en la base: {len(res)}")
            
            to_delete = []
            for row in res:
                case_id, title, text_content = row
                # Buscamos 'Horizonte' o 'San Vicente' o el código del contrato en el cuerpo del texto
                if any(word in (text_content or "") for word in ["Horizonte", "San Vicente", "LPN-2023-054"]):
                    print(f"🚩 ¡BLANCO DETECTADO! ID: {case_id} | Título: {title}")
                    to_delete.append(case_id)
            
            if not to_delete:
                print("❌ No se detectaron casos con esas palabras en el barrido secuencial.")
            else:
                for cid in to_delete:
                    # Borrar preguntas vinculadas
                    q_del = conn.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": cid})
                    # Borrar caso
                    c_del = conn.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": cid})
                    print(f"🗑️ Eliminado: {cid} ({q_del.rowcount} preguntas borradas)")
            
            # 2. Limpieza de preguntas huérfanas (sin caso) que mencionen el tema
            orphan_q = conn.execute(text("""
                DELETE FROM questions 
                WHERE stem LIKE '%Horizonte%' 
                   OR stem LIKE '%San Vicente%' 
                   OR stem LIKE '%LPN-2023-054%'
            """))
            print(f"🗑️ Preguntas huérfanas eliminadas: {orphan_q.rowcount}")

            # 3. EXTRA: Limpiar posibles rastros en tablas de rendimiento (por si acaso)
            # Esto evita que el "Smart Mix" intente recuperar preguntas borradas
            conn.execute(text("DELETE FROM question_performance WHERE question_id NOT IN (SELECT question_id FROM questions)"))
            
            conn.commit()
            print("🚀 OPERACIÓN COMPLETADA.")

    except Exception as e:
        print(f"🔥 Error: {e}")

if __name__ == "__main__":
    scorched_earth_purge()
