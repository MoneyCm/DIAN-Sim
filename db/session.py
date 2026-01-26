import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Configuración de la base de datos
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dian_sim.db"))

# Priority: Streamlit Secrets > Environment Variable > Local SQLite
try:
    import streamlit as st
    raw_url = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL", f"sqlite:///{db_path}"))
except:
    raw_url = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")

# Ensure PostgreSQL uses the correct driver for SQLAlchemy 2.0+
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

# Auto-create tables and handle migrations
from db.models import Base, User, UserOPEC, Attempt, UserStats, Achievement, Skill, QuestionPerformance, Configuration, Question
from sqlalchemy.orm import configure_mappers
from sqlalchemy import text
try:
    # 0. Ensure mappers are configured Mikey
    configure_mappers()

    # 1. Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Universal Migration Logic (SQLite & Postgres)
    db_type = "postgres" if "postgres" in DATABASE_URL.lower() else "sqlite"
    print(f"🔍 [SESSION] Database: {db_type.upper()} detected. Starting v18 Auto-Sync...")
    
    with engine.begin() as conn:
        new_cols_map = {
            "questions": ["macro_dominio", "micro_competencia"],
            "skills": [
                ("macro_dominio", "VARCHAR"), 
                ("micro_competencia", "VARCHAR"), 
                ("priority_weight", "FLOAT"),
                ("last_seen", "TIMESTAMP")
            ],
            "question_performance": [
                ("mastery_level", "FLOAT"),
                ("is_mastered", "BOOLEAN")
            ],
        }
        
        for table, cols in new_cols_map.items():
            # Check existing columns
            if db_type == "sqlite":
                existing_cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()]
            else:
                existing_cols = [row[0] for row in conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}';")).fetchall()]
            
            for col_info in cols:
                # Handle both simple strings and (name, type) tuples
                col_name = col_info[0] if isinstance(col_info, tuple) else col_info
                col_type = col_info[1] if isinstance(col_info, tuple) else "VARCHAR"
                
                if col_name not in existing_cols:
                    print(f"🔨 [SESSION] Adding column {col_name} to table {table}...")
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"))
                    except Exception as col_err:
                        print(f"⚠️ [SESSION] Could not add {col_name}: {col_err}")
        
    print("✅ [SESSION] Database schema synchronized for v18. Mikey.")

except Exception as e:
    print(f"❌ [SESSION] DATABASE ERROR: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
