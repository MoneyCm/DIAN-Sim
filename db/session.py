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
    # 1. Asegurar tablas
    Base.metadata.create_all(bind=engine)
    
    # 2. Lógica de Migración Automática v19
    print(f"🔍 [SESSION] Syncing {db_type.upper()} for v19... Mikey", file=sys.stderr)
    print(f"🔍 [SESSION] DB URL: {DATABASE_URL[:20]}...", file=sys.stderr)
    
    with engine.begin() as conn:
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
            # --- v40: Monetization Mikey ---
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
        
        for table, cols in new_cols_map.items():
            for col_info in cols:
                col_name, col_type = col_info
                try:
                    if db_type == "sqlite":
                        existing_cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()]
                        if col_name not in existing_cols:
                            print(f"🔨 [SESSION] Adding {col_name} to {table} (SQLite)...", file=sys.stderr)
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"))
                    else:
                        # Postgres: Use DO block for idempotent ADD COLUMN
                        print(f"🔨 [SESSION] Syncing {col_name} in {table} (Postgres)...", file=sys.stderr)
                        sql = f"""
                        DO $$ 
                        BEGIN 
                            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                           WHERE table_name='{table}' AND column_name='{col_name}') THEN 
                                ALTER TABLE {table} ADD COLUMN {col_name} {col_type}; 
                            END IF; 
                        END $$;
                        """
                        conn.execute(text(sql))
                except Exception as col_err:
                    print(f"⚠️ [SESSION] Fail syncing {col_name} in {table}: {col_err}", file=sys.stderr)
        
    print("✅ [SESSION] Sincronización v19 Completada con Éxito. Mikey", file=sys.stderr)

except Exception as e:
    print(f"❌ [SESSION] Error de DB en v19: {e}", file=sys.stderr)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
