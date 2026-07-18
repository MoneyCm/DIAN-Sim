import os
import sqlite3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def check_user_opecs(name, engine_or_conn):
    print(f"\n--- 📋 OPEC CONFIGURATIONS: {name} ---")
    try:
        if name == "NEON":
            with engine_or_conn.connect() as conn:
                res = conn.execute(text("""
                    SELECT u.id, u.username, o.opec_number, o.job_title, o.is_active, o.updated_at
                    FROM users u
                    LEFT JOIN user_opec o ON u.id = o.user_id
                """))
                rows = res.fetchall()
        else:
            cur = engine_or_conn.cursor()
            cur.execute("""
                SELECT u.id, u.username, o.opec_number, o.job_title, o.is_active, o.updated_at
                FROM users u
                LEFT JOIN user_opec o ON u.id = o.user_id
            """)
            rows = cur.fetchall()
            
        for r in rows:
            print(f"UserID: {r[0]} | User: {r[1]} | OPEC: {r[2]} | Title: {r[3]} | Active: {r[4]}")
    except Exception as e:
        print(f"Error {name}: {e}")

# Neon
url = os.getenv("DATABASE_URL")
if url: check_user_opecs("NEON", create_engine(url))

# SQLite
db_path = "dian_sim.db"
if os.path.exists(db_path): check_user_opecs("SQLITE", sqlite3.connect(db_path))
