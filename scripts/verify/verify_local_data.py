import sqlite3
import os

LOCAL_DB = "dian_sim.db"

if not os.path.exists(LOCAL_DB):
    print(f"❌ ERROR: No se encuentra {LOCAL_DB}")
    exit(1)

conn = sqlite3.connect(LOCAL_DB)
cursor = conn.cursor()

tables = ["users", "case_studies", "questions"]

print(f"🔍 Verificando datos LOCALES ({LOCAL_DB})...")

try:
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"📊 Tabla '{table}': {count} registros.")
except Exception as e:
    print(f"❌ Error al consultar SQLite: {e}")
finally:
    conn.close()
