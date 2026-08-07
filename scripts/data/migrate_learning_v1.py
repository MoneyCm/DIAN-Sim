"""Crea las tablas de aprendizaje V1 sin modificar datos existentes."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from db.models import Base  # noqa: E402
from db.session import engine  # noqa: E402


TABLES = ("learning_sessions", "learning_attempts", "topic_mastery", "ai_call_logs")


def main() -> None:
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind=engine, checkfirst=True)
        print(f"OK: {table_name}")


if __name__ == "__main__":
    main()
