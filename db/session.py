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

def sync_db_schema():
    """Función para sincronizar el esquema sin bloquear el inicio. mikey v6.3"""
    try:
        # 1. Asegurar tablas básicas
        Base.metadata.create_all(bind=engine)
        
        db_type = "postgres" if "postgres" in DATABASE_URL.lower() else "sqlite"
        print(f"🔧 [DB_SYNC] Modo: {db_type.upper()}. Mikey.", file=sys.stderr)
        
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        new_cols_map = {
            "questions": [("macro_dominio", "VARCHAR"), ("micro_competencia", "VARCHAR"), 
                          ("is_verified", "BOOLEAN DEFAULT FALSE"), ("quality_report", "JSON"),
                          ("global_hits", "INTEGER DEFAULT 0"), ("global_misses", "INTEGER DEFAULT 0"),
                          ("case_id", "VARCHAR"), ("question_type", "VARCHAR DEFAULT 'SITUATIONAL'")],
            "skills": [("macro_dominio", "VARCHAR"), ("micro_competencia", "VARCHAR"), 
                       ("priority_weight", "FLOAT"), ("last_seen", "TIMESTAMP")],
            "question_performance": [("mastery_level", "FLOAT"), ("is_mastered", "BOOLEAN"), ("is_favorite", "BOOLEAN DEFAULT FALSE")],
            "attempts": [("user_id", "INTEGER")],
            "users": [("subscription_tier", "VARCHAR DEFAULT 'free'"), ("subscription_expiry", "TIMESTAMP"), ("stripe_customer_id", "VARCHAR")],
            "user_stats": [("last_ia_date", "TIMESTAMP"), ("ia_count_today", "INTEGER DEFAULT 0")]
        }
        
        with engine.begin() as conn:
            for table, cols in new_cols_map.items():
                try:
                    # Verificar si la tabla existe primero
                    if table not in inspector.get_table_names():
                        print(f"⚠️ [DB_SYNC] Tabla {table} no existe aún. Mikey.", file=sys.stderr)
                        continue
                        
                    existing_cols = [c["name"] for c in inspector.get_columns(table)]
                    for col_name, col_type in cols:
                        if col_name not in existing_cols:
                            print(f"🔨 [DB_SYNC] Agregando {col_name} a {table}... Mikey.", file=sys.stderr)
                            try:
                                if db_type == "sqlite":
                                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"))
                                else:
                                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                            except Exception as col_err:
                                print(f"❌ [DB_SYNC] Error en columna {col_name}: {col_err}", file=sys.stderr)
                except Exception as table_err:
                    print(f"❌ [DB_SYNC] Error en tabla {table}: {table_err}", file=sys.stderr)
        print("✅ [DB_SYNC] Proceso finalizado. Mikey.", file=sys.stderr)
    except Exception as e:
        print(f"🔥 [DB_SYNC] Error crítico: {e}", file=sys.stderr)

# Ejecutar de forma segura al importar
sync_db_schema()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
