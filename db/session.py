import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# --- v19.0 LOGIC - MIKEY ---
load_dotenv()

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dian_sim.db"))

try:
    import streamlit as st
    raw_url = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL", f"sqlite:///{db_path}"))
except:
    raw_url = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")

if raw_url.startswith("postgres://") or raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

DATABASE_URL = raw_url

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True, 
    pool_recycle=300
)

# IMPORTANTE: Importamos modelos DESPUÉS de definir el motor
from db.models import Base, User, UserOPEC, Attempt, UserStats, Achievement, Skill, QuestionPerformance, Configuration, Question, CaseStudy

try:
    # 1. Asegurar tablas básicas (silencioso)
    Base.metadata.create_all(bind=engine)
    
    # 2. Lógica de Migración Automática v5.0 Mikey
    db_type = "postgres" if "postgres" in DATABASE_URL.lower() else "sqlite"
    print(f"🔍 [SESSION] Syncing {db_type.upper()} for v5.0... Mikey", file=sys.stderr)
    
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    new_cols_map = {
        "questions": [
            ("macro_dominio", "VARCHAR"), 
            ("micro_competencia", "VARCHAR"),
            ("is_verified", "BOOLEAN DEFAULT FALSE"),
            ("quality_report", "JSON"),
            ("global_hits", "INTEGER DEFAULT 0"),
            ("global_misses", "INTEGER DEFAULT 0"),
            ("case_id", "VARCHAR"),
            ("question_type", "VARCHAR DEFAULT 'SITUATIONAL'")
        ],
        "skills": [
            ("macro_dominio", "VARCHAR"), 
            ("micro_competencia", "VARCHAR"), 
            ("priority_weight", "FLOAT"),
            ("last_seen", "TIMESTAMP")
        ],
        "question_performance": [
            ("mastery_level", "FLOAT"),
            ("is_mastered", "BOOLEAN"),
            ("is_favorite", "BOOLEAN DEFAULT FALSE")
        ],
        "attempts": [
            ("user_id", "INTEGER")
        ],
        "users": [
            ("subscription_tier", "VARCHAR DEFAULT 'free'"),
            ("subscription_expiry", "TIMESTAMP"),
            ("stripe_customer_id", "VARCHAR")
        ],
        "user_stats": [
            ("last_ia_date", "TIMESTAMP"),
            ("ia_count_today", "INTEGER DEFAULT 0")
        ]
    }
    
    with engine.begin() as conn:
        for table, cols in new_cols_map.items():
            # Obtener columnas actuales usando inspector (seguro)
            try:
                existing_cols = [c["name"] for c in inspector.get_columns(table)]
                for col_name, col_type in cols:
                    if col_name not in existing_cols:
                        print(f"🔨 [SESSION] Adding {col_name} to {table}...", file=sys.stderr)
                        if db_type == "sqlite":
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"))
                        else:
                            # Postgres robusto con IF NOT EXISTS
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
            except Exception as table_err:
                print(f"⚠️ [SESSION] Table {table} skipped or not ready: {table_err}", file=sys.stderr)
                
    print("✅ [SESSION] Sincronización v5.0 Completada. Mikey", file=sys.stderr)

except Exception as e:
    print(f"❌ [SESSION] Critical Import Error (Handled): {e}", file=sys.stderr)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
