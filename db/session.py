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

# Logging connection target for clarity
if "sqlite" in DATABASE_URL:
    print(f"🏠 CONNECTING TO: Local SQLite Database ({db_path})")
else:
    # Mask password for security in logs
    masked_url = DATABASE_URL
    if "@" in DATABASE_URL:
        parts = DATABASE_URL.split("@")
        masked_url = parts[0].split(":")[0] + ":****@" + parts[1]
    print(f"🌐 CONNECTING TO: Cloud Database ({masked_url})")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,  # Crucial for cloud databases like Supabase
    pool_recycle=300     # Recycle connections every 5 minutes
)

# Auto-create tables and handle migrations
from db.models import Base, User, UserOPEC, Attempt, UserStats, Achievement, Skill, QuestionPerformance, Configuration, Question
from sqlalchemy.orm import configure_mappers
from sqlalchemy import text
try:
    # 0. Ensure mappers are configured Mikey
    # Esto ahora usará el Singleton definido en models.py
    configure_mappers()

    # 1. Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Universal Migration Logic (SQLite & Postgres)
    db_type = "postgres" if "postgres" in DATABASE_URL.lower() else "sqlite"
    print(f"🔍 Database: {db_type.upper()} detected. Checking schema synchronization...")
    
    with engine.begin() as conn:
        # Tables to check
        tables_to_migrate = ["questions", "skills", "configurations", "users", "user_opec", "attempts", "user_stats", "question_performance", "achievements"]
        new_cols_map = {
            "questions": ["macro_dominio", "micro_competencia"],
            "skills": ["macro_dominio", "micro_competencia", "user_id"],
            "attempts": ["user_id"],
            "user_stats": ["user_id"],
            "user_opec": ["user_id"],
            "question_performance": ["user_id"],
            "achievements": ["user_id"],
            "configurations": [] 
        }
        
        for table in tables_to_migrate:
            # Check existing columns
            if db_type == "sqlite":
                # Ensure table exists first in SQLite if not created by metadata
                conn.execute(text(f"CREATE TABLE IF NOT EXISTS {table} (id_temp_init INTEGER PRIMARY KEY)"))
                existing_cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()]
            else:
                # Postgres
                existing_cols = [row[0] for row in conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}';")).fetchall()]
            
            for col in new_cols_map.get(table, []):
                if col not in existing_cols:
                    print(f"🔨 Adding column {col} to table {table}...")
                    col_type = "INTEGER" if col == "user_id" else "VARCHAR"
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
        
        print("✅ Database schema synchronized successfully for Fase 3 (Users).")

except Exception as e:
    # In Streamlit Cloud, this will show up in the Logs (Manage App -> Logs)
    print(f"❌ DATABASE MIGRATION ERROR: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- v5.0 NEW: High-Performance Caching ---
def get_cached_opec_list():
    """Retorna la lista de OPECs con cache (60 min) para máxima velocidad. Mikey"""
    import streamlit as st
    @st.cache_data(ttl=3600)
    def _fetch():
        db = SessionLocal()
        # Use the already imported model
        results = db.query(UserOPEC).limit(100).all()
        db.close()
        return results
    return _fetch()
