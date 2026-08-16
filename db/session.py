import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# --- v19.0 LOGIC - MIKEY ---
load_dotenv()

# Tests must never inherit a developer or production DATABASE_URL from .env.
# This guard is evaluated before Streamlit secrets so collection cannot contact
# an external database accidentally.
TESTING = os.getenv("DIAN_SIM_TESTING", "").lower() in ("1", "true", "yes")

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dian_sim.db"))

class MissingDatabaseURLError(RuntimeError):
    """Raised when a managed environment has no configured remote database."""


def _truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes")


def _requires_remote_database():
    return _truthy(os.getenv("REQUIRE_DATABASE_URL")) or os.getenv(
        "DIAN_SIM_ENV", "development"
    ).strip().lower() in ("production", "prod", "cloud")


def _streamlit_database_url():
    import streamlit as st
    # v19.4 - DetecciÃ³n Profunda de DATABASE_URL
    secrets_url = st.secrets.get("DATABASE_URL")

    # Debug: Imprimir llaves disponibles en stderr
    print(f"ðŸ•µï¸ [DB] Streamlit Secrets detectados: {list(st.secrets.keys())}", file=sys.stderr)

    if not secrets_url:
        for section in st.secrets:
            # En Streamlit, las secciones se acceden como atributos o llaves
            try:
                content = st.secrets[section]
                if hasattr(content, "get") and content.get("DATABASE_URL"):
                    secrets_url = content.get("DATABASE_URL")
                    print(f"ðŸ”— [DB] DATABASE_URL encontrada en [{section}].", file=sys.stderr)
                    break
            except: continue

    return secrets_url


def _resolve_database_url(*, testing=TESTING):
    if testing:
        print("[DB] Pruebas: usando SQLite aislado en memoria.", file=sys.stderr)
        return "sqlite:///:memory:"

    env_url = os.getenv("DATABASE_URL", "").strip()
    try:
        secrets_url = _streamlit_database_url()
    except Exception as exc:
        print(
            f"âŒ [DB] Error accediendo a secrets: {type(exc).__name__}",
            file=sys.stderr,
        )
        if _requires_remote_database() and not env_url:
            raise MissingDatabaseURLError(
                "DATABASE_URL es obligatoria en producción; configura Streamlit "
                "Secrets o variables de entorno."
            ) from exc
        secrets_url = None

    if secrets_url:
        print("ðŸ”— [DB] Usando DATABASE_URL de Streamlit Secrets.", file=sys.stderr)
        return secrets_url
    elif env_url:
        print("ðŸ”— [DB] Usando DATABASE_URL de Environment Variables.", file=sys.stderr)
        return env_url
    if _requires_remote_database():
        raise MissingDatabaseURLError(
            "DATABASE_URL es obligatoria en producción; configura Streamlit "
            "Secrets o variables de entorno."
        )
    print("[DB] Desarrollo local: usando SQLite.", file=sys.stderr)
    return f"sqlite:///{db_path}"


raw_url = _resolve_database_url()

if raw_url.startswith("postgres://") or raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # v19.3 - Limpiar parÃ¡metros conflictivos de Neon
    if "channel_binding=" in raw_url:
        import re
        raw_url = re.sub(r'[&?]channel_binding=[^&]*', '', raw_url)

DATABASE_URL = raw_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
    pool_recycle=300
)

# Enable WAL Mode for SQLite concurrency
if "sqlite" in DATABASE_URL:
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# IMPORTANTE: Importamos modelos DESPUÃ‰S de definir el motor
from db.models import Base, User, UserOPEC, Attempt, UserStats, Achievement, Skill, QuestionPerformance, Configuration, Question, CaseStudy, Competition

def sync_db_schema():
    """FunciÃ³n para sincronizar el esquema sin bloquear el inicio. mikey v6.3"""
    try:
        # 1. Asegurar tablas bÃ¡sicas
        Base.metadata.create_all(bind=engine)

        db_type = "postgres" if "postgres" in DATABASE_URL.lower() else "sqlite"
        print(f"ðŸ”§ [DB_SYNC] Modo: {db_type.upper()}. Mikey.", file=sys.stderr)

        from sqlalchemy import inspect
        inspector = inspect(engine)

        new_cols_map = {
            "normativa_chunks": [("embedding_json", "TEXT")],
            "user_opec": [("competition_id", "INTEGER")],
            "case_studies": [("competition_id", "INTEGER")],
            "questions": [("competition_id", "INTEGER"), ("macro_dominio", "VARCHAR"), ("micro_competencia", "VARCHAR"),
                          ("is_verified", "BOOLEAN DEFAULT FALSE"), ("quality_report", "JSON"),
                          ("global_hits", "INTEGER DEFAULT 0"), ("global_misses", "INTEGER DEFAULT 0"),
                          ("case_id", "VARCHAR"), ("question_type", "VARCHAR DEFAULT 'SITUATIONAL'")],
            "skills": [("competition_id", "INTEGER"), ("macro_dominio", "VARCHAR"), ("micro_competencia", "VARCHAR"),
                       ("priority_weight", "FLOAT"), ("last_seen", "TIMESTAMP")],
            "question_performance": [("mastery_level", "FLOAT"), ("is_mastered", "BOOLEAN"), ("is_favorite", "BOOLEAN DEFAULT FALSE"),
                                     ("next_review", "TIMESTAMP"), ("review_interval_days", "FLOAT DEFAULT 0"),
                                     ("ease_factor", "FLOAT DEFAULT 2.5"), ("review_count", "INTEGER DEFAULT 0"),
                                     ("lapse_count", "INTEGER DEFAULT 0"), ("last_confidence", "VARCHAR(20)"),
                                     ("last_error_type", "VARCHAR(50)"), ("last_reviewed_at", "TIMESTAMP")],
            "attempts": [("user_id", "INTEGER")],
            "users": [("subscription_tier", "VARCHAR DEFAULT 'free'"), ("subscription_expiry", "TIMESTAMP"), ("stripe_customer_id", "VARCHAR")],
            "user_stats": [("last_ia_date", "TIMESTAMP"), ("ia_count_today", "INTEGER DEFAULT 0")]
        }

        with engine.begin() as conn:
            for table, cols in new_cols_map.items():
                try:
                    # Verificar si la tabla existe primero
                    if table not in inspector.get_table_names():
                        print(f"âš ï¸ [DB_SYNC] Tabla {table} no existe aÃºn. Mikey.", file=sys.stderr)
                        continue

                    existing_cols = [c["name"] for c in inspector.get_columns(table)]
                    for col_name, col_type in cols:
                        if col_name not in existing_cols:
                            print(f"ðŸ”¨ [DB_SYNC] Agregando {col_name} a {table}... Mikey.", file=sys.stderr)
                            try:
                                if db_type == "sqlite":
                                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};"))
                                else:
                                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                            except Exception as col_err:
                                print(
                                    f"âŒ [DB_SYNC] Error en columna {col_name}: "
                                    f"{type(col_err).__name__}",
                                    file=sys.stderr,
                                )
                except Exception as table_err:
                    print(
                        f"âŒ [DB_SYNC] Error en tabla {table}: "
                        f"{type(table_err).__name__}",
                        file=sys.stderr,
                    )
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO competitions (code, name, entity, description, is_active, created_at)
                SELECT 'DIAN-2676', 'DIAN 2676 - Ingreso', 'DIAN',
                       'Proceso de selecciÃ³n DIAN migrado desde el banco original', TRUE, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (SELECT 1 FROM competitions WHERE code = 'DIAN-2676')
            """))
            default_competition_id = conn.execute(
                text("SELECT id FROM competitions WHERE code = 'DIAN-2676'")
            ).scalar()
            for table in ("user_opec", "case_studies", "questions", "skills"):
                conn.execute(text(
                    f"UPDATE {table} SET competition_id = :competition_id "
                    "WHERE competition_id IS NULL"
                ), {"competition_id": default_competition_id})
        print("âœ… [DB_SYNC] Proceso finalizado. Mikey.", file=sys.stderr)
    except Exception as e:
        print(
            f"ðŸ”¥ [DB_SYNC] Error crÃ­tico: {type(e).__name__}",
            file=sys.stderr,
        )

    # Emergency Fix for Missing Columns (Brute Force - SQLite Native)
    try:
        import sqlite3
        if DATABASE_URL == f"sqlite:///{db_path}":
            # Local connection to bypass engine entirely
            print("ðŸ”§ [DB_SYNC] Native SQLite Fix.", file=sys.stderr)
            conn_native = sqlite3.connect(db_path, timeout=30)
            cur = conn_native.cursor()

            # last_ia_date
            try:
                cur.execute("ALTER TABLE user_stats ADD COLUMN last_ia_date TIMESTAMP")
                print("âœ… [DB_SYNC] Native Added: last_ia_date", file=sys.stderr)
            except Exception:
                pass # Exists

            # ia_count_today
            try:
                cur.execute("ALTER TABLE user_stats ADD COLUMN ia_count_today INTEGER DEFAULT 0")
                print("âœ… [DB_SYNC] Native Added: ia_count_today", file=sys.stderr)
            except Exception:
                pass # Exists

            conn_native.commit()
            conn_native.close()
        else:
            # Keep sqlalchemy fix for non-sqlite
            with engine.connect() as conn:
                try:
                   conn.execute(text("ALTER TABLE user_stats ADD COLUMN IF NOT EXISTS last_ia_date TIMESTAMP;"))
                except: pass
                try:
                   conn.execute(text("ALTER TABLE user_stats ADD COLUMN IF NOT EXISTS ia_count_today INTEGER DEFAULT 0;"))
                except: pass
                conn.commit()

    except Exception as e:
        print(
            f"âš ï¸ [DB_SYNC] Native fix error: {type(e).__name__}",
            file=sys.stderr,
        )

# La sincronización del esquema es una tarea de despliegue/mantenimiento, no
# de cada carga de Streamlit. En Neon implicaba inspecciones y ALTER/UPDATE
# innecesarios antes de atender al usuario, ralentizando el Dashboard.
# SQLite local conserva el comportamiento cómodo de desarrollo; para forzar
# una sincronización remota se usa AUTO_MIGRATE_SCHEMA=true una sola vez.
auto_migrate = os.getenv("AUTO_MIGRATE_SCHEMA", "").lower() in ("1", "true", "yes")
if "sqlite" in DATABASE_URL or auto_migrate:
    sync_db_schema()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


