
import os, sys
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

# We need to trigger session.py to run the migrations BEFORE we do our own logic
from db.session import SessionLocal, DATABASE_URL
from db.models import Question, Attempt, User, QuestionPerformance

def sync_master():
    print("🚀 Iniciando MEGA-SYNC v48.5.3 (Mikey Edition)")
    
    # 1. Database Connections
    local_db_path = os.path.join(PROJECT_ROOT, "dian_sim.db")
    cloud_url = os.getenv("DATABASE_URL")
    
    if not cloud_url or "sqlite" in cloud_url.lower():
        print("❌ Error: DATABASE_URL no configurada para la nube (Supabase).")
        return

    # FORZAR MOTOR LOCAL SQLITE (Aunque el .env diga Cloud)
    from sqlalchemy import create_engine
    engine_local = create_engine(f"sqlite:///{local_db_path}")
    SessionLocalSQLite = sessionmaker(bind=engine_local)
    db_local = SessionLocalSQLite()
    
    # 2. Assign 'cesar' (ID 2) to all orphan attempts in local
    print("🔧 Reparando intentos locales huérfanos...")
    conn_raw = sqlite3.connect(local_db_path)
    try:
        # Assign to user 2 (Cesar) if user_id is null
        conn_raw.execute("UPDATE attempts SET user_id = 2 WHERE user_id IS NULL;")
        conn_raw.commit()
    except Exception as e:
        print(f"⚠️ Error reparando intentos: {e}")
    finally:
        conn_raw.close()

    # 3. Synchronize Questions (Local -> Cloud)
    print("📡 Sincronizando Preguntas (Local -> Nube)...")
    questions_local = db_local.query(Question).all()
    
    engine_cloud = create_engine(cloud_url)
    SessionCloud = sessionmaker(bind=engine_cloud)
    db_cloud = SessionCloud()
    
    added_q = 0
    for q in questions_local:
        # Check by hash
        exists = db_cloud.query(Question).filter_by(hash_norm=q.hash_norm).first()
        if not exists:
            # Clone object (fast way)
            q_data = {c.name: getattr(q, c.name) for c in q.__table__.columns}
            new_q = Question(**q_data)
            db_cloud.add(new_q)
            added_q += 1
            if added_q % 50 == 0:
                db_cloud.commit()
    db_cloud.commit()
    print(f"✅ Preguntas subidas: {added_q}")

    # 4. Synchronize Attempts (Local -> Cloud)
    print("📡 Sincronizando Intentos (Local -> Nube)...")
    # Note: We use raw query because of potential primary key conflicts or uuid vs id
    attempts_local = db_local.query(Attempt).all()
    added_a = 0
    for a in attempts_local:
        # Check by ID or combination for safety
        exists = db_cloud.query(Attempt).filter_by(attempt_id=a.attempt_id).first()
        if not exists:
            a_data = {c.name: getattr(a, c.name) for c in a.__table__.columns}
            new_a = Attempt(**a_data)
            db_cloud.add(new_a)
            added_a += 1
    db_cloud.commit()
    print(f"✅ Intentos subidos: {added_a}")

    print("\n🎉 MEGA-SYNC FINALIZADO EXITOSAMENTE.")
    db_local.close()
    db_cloud.close()

if __name__ == "__main__":
    sync_master()
