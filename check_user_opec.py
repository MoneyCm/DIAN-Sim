import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- 📊 CONTENIDO DE LA TABLA USER_OPEC ---")
        result = conn.execute(text("SELECT id, user_id, opec_number, job_title, is_active FROM user_opec"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row.id} | UserID: {row.user_id} | OPEC: {row.opec_number} | Title: {row.job_title} | Active: {row.is_active}")
        
        print("\n--- 👤 CONTENIDO DE LA TABLA USERS ---")
        result = conn.execute(text("SELECT id, username FROM users"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row.id} | Username: {row.username}")
            
except Exception as e:
    print(f"Error: {e}")
