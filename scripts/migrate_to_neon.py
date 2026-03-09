import sqlite3
import os
import sys
from pathlib import Path

# Agregar la raíz del proyecto al sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()
LOCAL_DB = "dian_sim.db"
NEON_URL = os.getenv("DATABASE_URL")

if not NEON_URL or "neon.tech" not in NEON_URL:
    print("❌ ERROR: No se encontró una URL de Neon válida en el archivo .env")
    exit(1)

print(f"🚀 Iniciando migración a Neon...")

# Conexión local (SQLite)
conn_sqlite = sqlite3.connect(LOCAL_DB)
cursor_sqlite = conn_sqlite.cursor()

# Conexión remota (Neon/PostgreSQL)
engine_neon = create_engine(NEON_URL)
SessionNeon = sessionmaker(bind=engine_neon)
session_neon = SessionNeon()

def migrate_table(table_name, id_col="id"):
    print(f"📦 Migrando tabla: {table_name}...")
    cursor_sqlite.execute(f"SELECT * FROM {table_name}")
    rows = cursor_sqlite.fetchall()
    
    if not rows:
        print(f"  Empty table {table_name}, skipping.")
        return

    # Obtener nombres de columnas de SQLite
    cursor_sqlite.execute(f"PRAGMA table_info({table_name})")
    cols_sqlite = [info[1] for info in cursor_sqlite.fetchall()]
    
    # Obtener columnas de la tabla en Neon
    from sqlalchemy import inspect
    inspector = inspect(engine_neon)
    columns_neon = [c["name"] for c in inspector.get_columns(table_name)]
    
    col_str = ", ".join(columns_neon)
    placeholders = ", ".join([f":{c}" for c in columns_neon])
    sql = text(f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT ({id_col}) DO NOTHING")
    
    count = 0
    errors = 0
    for row in rows:
        data_sqlite = dict(zip(cols_sqlite, row))
        data_final = {}
        
        for col in columns_neon:
            val = data_sqlite.get(col)
            
            # 1. Booleanos
            if col in ["is_verified", "is_active"]:
                val = bool(val) if val is not None else (True if col == "is_active" else False)
            
            # 2. JSON (Neon espera JSON, pero el driver psycopg2 necesita strings si no se usan adaptadores)
            if col in ["options_json", "quality_report"]:
                import json
                if isinstance(val, str):
                    try:
                        # Validar si ya es JSON válido
                        json.loads(val)
                    except:
                        # Si no es JSON válido, convertir a nulo o dejar como está
                        val = None
                elif isinstance(val, (dict, list)):
                    try:
                        val = json.dumps(val)
                    except:
                        val = None
            
            # 3. Timestamps
            if col == "created_at" and isinstance(val, str):
                from datetime import datetime
                try:
                    # Intentar ISO o formatos comunes de SQLite
                    val = val.replace(" ", "T") # Convertir a ISO-ish
                except:
                    pass

            # 4. Defaults
            if val is None and col == "subscription_tier":
                val = "free"

            data_final[col] = val
        
        try:
            session_neon.execute(sql, data_final)
            count += 1
            if count % 200 == 0:
                session_neon.commit()
                print(f"  ... {count} registros insertados en {table_name}.")
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  ⚠️ Error en fila {data_final.get(id_col)}: {str(e)[:300]}...")
            session_neon.rollback()
    
    session_neon.commit()
    print(f"  ✅ {count} registros exitosos en {table_name}. ({errors} errores)")

try:
    # 1. Sincronizar esquema primero (usando la lógica interna de la app)
    print("📋 Sincronizando esquema en Neon...")
    from db.session import sync_db_schema
    sync_db_schema()

    # 2. Migrar datos maestros
    tables_to_migrate = [
        ("case_studies", "id"),
        ("users", "id"),
        ("questions", "question_id")
    ]
    
    for table, pk in tables_to_migrate:
        migrate_table(table, pk)
    
    print("\n✨ ¡MIGRACIÓN COMPLETADA EXITOSAMENTE! ✨")
    print("Ahora tu versión en la nube tiene todos tus datos locales.")

except Exception as e:
    import traceback
    print(f"🔥 ERROR CRÍTICO:\n{traceback.format_exc()}")
    session_neon.rollback()
finally:
    conn_sqlite.close()
    session_neon.close()
