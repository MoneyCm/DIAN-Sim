import os
import sqlite3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# --- 1. LIMPIEZA EN NEON (CLOUD) ---
NEON_URL = os.getenv("DATABASE_URL")
if NEON_URL:
    try:
        engine = create_engine(NEON_URL)
        with engine.connect() as conn:
            print("--- 🔥 LIMPIANDO NEON ---")
            terms = ['%Soluciones SAS%', '%Villaflores%', '%Constructora Horizonte%', '%CNSC%', '%Comisión Nacional del Servicio Civil%']
            t_q = 0
            t_c = 0
            for t in terms:
                t_q += conn.execute(text("DELETE FROM questions WHERE stem ILIKE :t OR rationale ILIKE :t"), {"t": t}).rowcount
                t_c += conn.execute(text("DELETE FROM case_studies WHERE text ILIKE :t OR title ILIKE :t"), {"t": t}).rowcount
            conn.commit()
            print(f"Neon: {t_q} preguntas y {t_c} casos eliminados.")
    except Exception as e:
        print(f"Error Neon: {e}")

# --- 2. LIMPIEZA EN SQLITE (LOCAL) ---
DB_PATH = "dian_sim.db"
if os.path.exists(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        print("--- 🔥 LIMPIANDO SQLITE LOCAL ---")
        terms = ['%Soluciones SAS%', '%Villaflores%', '%Constructora Horizonte%', '%CNSC%', '%Comisión Nacional del Servicio Civil%']
        t_q = 0
        t_c = 0
        for t in terms:
            cur.execute("DELETE FROM questions WHERE stem LIKE ? OR rationale LIKE ?", (t, t))
            t_q += cur.rowcount
            cur.execute("DELETE FROM case_studies WHERE text LIKE ? OR title LIKE ?", (t, t))
            t_c += cur.rowcount
        conn.commit()
        conn.close()
        print(f"SQLite: {t_q} preguntas y {t_c} casos eliminados.")
    except Exception as e:
        print(f"Error SQLite: {e}")

print("✅ Limpieza dual completada.")
