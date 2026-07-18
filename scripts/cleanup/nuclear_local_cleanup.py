
import os
import sqlite3
from sqlalchemy import create_engine, text

# Ruta absoluta a la base de datos local
db_path = os.path.abspath("dian_sim.db")

def nuclear_local_cleanup():
    print(f"☢️ Iniciando limpieza nuclear en: {db_path}")
    
    # 1. Conexión nativa para forzar cambios de esquema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Arreglar esquema de la tabla 'skills'
        print("🔧 Corrigiendo esquema de 'skills'...")
        cursor.execute("PRAGMA table_info(skills)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            cursor.execute("ALTER TABLE skills ADD COLUMN user_id INTEGER")
            print("✅ Columna 'user_id' agregada a 'skills'.")
        
        # 2. Borrado total de datos
        print("🗑️ Borrando todos los datos de casos y preguntas locales...")
        cursor.execute("DELETE FROM questions")
        cursor.execute("DELETE FROM case_studies")
        cursor.execute("DELETE FROM skills")
        cursor.execute("DELETE FROM attempts")
        cursor.execute("DELETE FROM question_performance")
        
        conn.commit()
        print("✨ SQLite local completamente limpio y actualizado.")
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    nuclear_local_cleanup()
