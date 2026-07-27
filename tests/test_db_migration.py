import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import engine
from sqlalchemy import inspect

def test_column_exists():
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("normativa_chunks")]
    assert "embedding_json" in columns, "La columna embedding_json debe estar en normativa_chunks"
    assert "question_anki_enrichments" in inspector.get_table_names()
    assert "competitions" in inspector.get_table_names()
    for table in ("user_opec", "case_studies", "questions", "skills"):
        table_columns = {column["name"] for column in inspector.get_columns(table)}
        assert "competition_id" in table_columns
    print("Prueba de migracion de columna exitosa.")

if __name__ == "__main__":
    test_column_exists()
