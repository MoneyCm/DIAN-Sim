import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- 🎯 ASIGNANDO OPEC 236769 A CESAR (ID 2) ---")
        from datetime import datetime
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO user_opec (user_id, opec_number, job_title, level, purpose, functions, is_active, updated_at)
            VALUES (2, '236769', 'Gestor III', 'Profesional', 
            'Adelantar los procesos de fiscalización tributaria, aduanera y cambiaria.', 
            '["Realizar auditorías", "Proferir actos administrativos", "Atender requerimientos"]', true, :now)
        """), {"now": now})
        conn.commit()
        print("✅ OPEC 236769 asignada y activada exitosamente.")
except Exception as e:
    print(f"Error: {e}")
