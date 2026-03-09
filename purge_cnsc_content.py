import argparse
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

BANNED_PATTERNS = [
    "%Comision Nacional del Servicio Civil%",
    "%CNSC%",
    "%Constructora Horizonte%",
    "%Horizonte S.A.%",
    "%Alcaldia Municipal%",
    "%San Vicente%",
    "%LPN-2023-054%",
    "%contratacion publica%",
    "%SIPR%",
]

case_terms = []
for i in range(len(BANNED_PATTERNS)):
    case_terms.append(f"title ILIKE :p{i}")
    case_terms.append(f"text ILIKE :p{i}")
    case_terms.append(f"topic ILIKE :p{i}")
CASE_WHERE = " OR ".join(case_terms)

question_terms = []
for i in range(len(BANNED_PATTERNS)):
    question_terms.append(f"stem ILIKE :p{i}")
    question_terms.append(f"rationale ILIKE :p{i}")
    question_terms.append(f"topic ILIKE :p{i}")
    question_terms.append(f"competency ILIKE :p{i}")
QUESTION_WHERE = " OR ".join(question_terms)

PARAMS = {f"p{i}": pattern for i, pattern in enumerate(BANNED_PATTERNS)}


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and delete CNSC/public procurement content in Neon."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run deletion. Without this flag it only shows a preview.",
    )
    args = parser.parse_args()

    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is not configured.")

    if "postgres" not in DATABASE_URL.lower() and "neon.tech" not in DATABASE_URL.lower():
        raise SystemExit("This script is intended for Neon/Postgres. Check DATABASE_URL before running it.")

    engine = create_engine(DATABASE_URL)

    preview_cases_sql = text(
        f"""
        SELECT id, title, topic
        FROM case_studies
        WHERE {CASE_WHERE}
        ORDER BY created_at DESC
        LIMIT 25
        """
    )
    preview_questions_sql = text(
        f"""
        SELECT question_id, case_id, LEFT(stem, 180) AS stem_preview
        FROM questions
        WHERE {QUESTION_WHERE}
           OR case_id IN (SELECT id FROM case_studies WHERE {CASE_WHERE})
        ORDER BY created_at DESC
        LIMIT 25
        """
    )
    count_cases_sql = text(f"SELECT COUNT(*) FROM case_studies WHERE {CASE_WHERE}")
    count_questions_sql = text(
        f"""
        SELECT COUNT(*)
        FROM questions
        WHERE {QUESTION_WHERE}
           OR case_id IN (SELECT id FROM case_studies WHERE {CASE_WHERE})
        """
    )
    delete_questions_sql = text(
        f"""
        DELETE FROM questions
        WHERE {QUESTION_WHERE}
           OR case_id IN (SELECT id FROM case_studies WHERE {CASE_WHERE})
        """
    )
    delete_cases_sql = text(f"DELETE FROM case_studies WHERE {CASE_WHERE}")

    with engine.begin() as conn:
        case_count = conn.execute(count_cases_sql, PARAMS).scalar() or 0
        question_count = conn.execute(count_questions_sql, PARAMS).scalar() or 0
        print("--- Preview of CNSC/public procurement cleanup ---")
        print(f"Candidate cases: {case_count}")
        print(f"Candidate questions: {question_count}")

        if case_count:
            print("\nDetected cases:")
            for row in conn.execute(preview_cases_sql, PARAMS).fetchall():
                print(f"- case_id={row.id} | title={row.title} | topic={row.topic}")

        if question_count:
            print("\nDetected questions:")
            for row in conn.execute(preview_questions_sql, PARAMS).fetchall():
                print(f"- question_id={row.question_id} | case_id={row.case_id} | stem={row.stem_preview}")

        if not args.apply:
            print("\nPreview mode only. Run with --apply to delete.")
            return

        deleted_questions = conn.execute(delete_questions_sql, PARAMS).rowcount or 0
        deleted_cases = conn.execute(delete_cases_sql, PARAMS).rowcount or 0
        print("\nCleanup applied successfully.")
        print(f"Deleted questions: {deleted_questions}")
        print(f"Deleted cases: {deleted_cases}")


if __name__ == "__main__":
    main()
