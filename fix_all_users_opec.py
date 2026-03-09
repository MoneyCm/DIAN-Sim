import os
import sqlite3
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
now = datetime.now()

OPEC_DATA = {
    "opec_number": "236769",
    "job_title": "Gestor III",
    "level": "Profesional",
    "purpose": "Adelantar los procesos de fiscalización tributaria, aduanera y cambiaria.",
    "functions": '["Realizar auditorías", "Proferir actos administrativos", "Atender requerimientos"]',
    "requirements": "Título de PROFESIONAL en NBC: ADMINISTRACION ,O, NBC: CIENCIA POLITICA, RELACIONES INTERNACIONALES ,O, NBC: CONTADURIA PUBLICA ,O, NBC: DERECHO Y AFINES ,O, NBC: ECONOMIA ,O, NBC: INGENIERIA ADMINISTRATIVA Y AFINES ,O, NBC: INGENIERIA DE SISTEMAS, TELEMATICA Y AFINES ,O, NBC: INGENIERIA INDUSTRIAL Y AFINES ,O, NBC: INGENIERIA QUIMICA Y AFINES ,O, NBC: MATEMATICAS, ESTADISTICA Y AFINES."
}

def fix_user_opecs(name, engine_or_conn):
    print(f"--- 🎯 CONFIGURANDO OPEC PARA TODOS LOS USUARIOS: {name} ---")
    try:
        if name == "NEON":
            with engine_or_conn.connect() as conn:
                # Get all users
                users = conn.execute(text("SELECT id FROM users")).fetchall()
                for u in users:
                    u_id = u[0]
                    # Borrar anteriores para evitar duplicados si no hay UNIQUE constraint
                    conn.execute(text("DELETE FROM user_opec WHERE user_id = :id"), {"id": u_id})
                    conn.execute(text("""
                        INSERT INTO user_opec (user_id, opec_number, job_title, level, purpose, functions, requirements, is_active, updated_at)
                        VALUES (:id, :opec, :title, :lvl, :purp, :funcs, :reqs, true, :now)
                    """), {
                        "id": u_id, "opec": OPEC_DATA["opec_number"], "title": OPEC_DATA["job_title"],
                        "lvl": OPEC_DATA["level"], "purp": OPEC_DATA["purpose"], "funcs": OPEC_DATA["functions"],
                        "reqs": OPEC_DATA["requirements"], "now": now
                    })
                conn.commit()
        else:
            cur = engine_or_conn.cursor()
            cur.execute("SELECT id FROM users")
            users = cur.fetchall()
            for u in users:
                u_id = u[0]
                cur.execute("DELETE FROM user_opec WHERE user_id = ?", (u_id,))
                cur.execute("""
                    INSERT INTO user_opec (user_id, opec_number, job_title, level, purpose, functions, requirements, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (
                    u_id, OPEC_DATA["opec_number"], OPEC_DATA["job_title"],
                    OPEC_DATA["level"], OPEC_DATA["purpose"], OPEC_DATA["functions"],
                    OPEC_DATA["requirements"], now.isoformat()
                ))
            engine_or_conn.commit()
        print(f"✅ {name}: Listo.")
    except Exception as e:
        print(f"❌ {name} Error: {e}")

# Neon
url = os.getenv("DATABASE_URL")
if url: fix_user_opecs("NEON", create_engine(url))

# SQLite
db_path = "dian_sim.db"
if os.path.exists(db_path): fix_user_opecs("SQLITE", sqlite3.connect(db_path))
