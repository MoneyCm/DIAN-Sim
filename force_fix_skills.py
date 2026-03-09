
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import DATABASE_URL, db_path

def fix_skills_table(url, name):
    print(f"🔧 Arreglando tabla 'skills' en {name}...")
    try:
        engine = create_engine(url)
        with engine.begin() as conn:
            # Verificar si la columna user_id existe
            if "postgres" in url:
                check_sql = "SELECT column_name FROM information_schema.columns WHERE table_name='skills' AND column_name='user_id';"
            else:
                check_sql = "PRAGMA table_info(skills);"
            
            res = conn.execute(text(check_sql)).fetchall()
            has_user_id = False
            
            if "postgres" in url:
                has_user_id = len(res) > 0
            else:
                has_user_id = any(row[1] == 'user_id' for row in res)

            if not has_user_id:
                print(f"🔨 Agregando columna 'user_id' a 'skills' en {name}...")
                if "postgres" in url:
                    conn.execute(text("ALTER TABLE skills ADD COLUMN user_id INTEGER;"))
                else:
                    conn.execute(text("ALTER TABLE skills ADD COLUMN user_id INTEGER;"))
                print(f"✅ Columna agregada en {name}.")
            else:
                print(f"✔ La columna 'user_id' ya existe en {name}.")
    except Exception as e:
        print(f"❌ Error en {name}: {e}")

if __name__ == "__main__":
    # 1. Arreglar Neon (Postgres)
    if "neon" in DATABASE_URL or "postgres" in DATABASE_URL:
        fix_skills_table(DATABASE_URL, "Neon (Remote)")
    
    # 2. Arreglar SQLite local (por si la app cae ahí)
    local_url = f"sqlite:///{db_path}"
    fix_skills_table(local_url, "SQLite (Local)")
