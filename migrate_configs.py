import sqlite3
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    print("--- 🔍 EXTRAYENDO CONFIGS DE SQLITE LOCAL ---")
    conn_sqlite = sqlite3.connect("dian_sim.db")
    cursor = conn_sqlite.cursor()
    cursor.execute("SELECT key_name, value FROM configurations")
    configs = cursor.fetchall()
    conn_sqlite.close()

    if not configs:
        print("No se encontraron configuraciones en la base de datos local.")
    else:
        print(f"Encontradas {len(configs)} configuraciones locales.")
        with engine.connect() as conn:
            for key, val in configs:
                print(f"Migrando {key} a Neon...")
                conn.execute(text("""
                    INSERT INTO configurations (key_name, value) 
                    VALUES (:key, :val) 
                    ON CONFLICT (key_name) DO UPDATE SET value = :val
                """), {"key": key, "val": val})
            conn.commit()
            print("✅ Migración de configuraciones completada.")

except Exception as e:
    print(f"Error: {e}")
