
import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
from db.session import SessionLocal

def search_questions_for_horizonte():
    db = SessionLocal()
    try:
        # Search in questions stem
        query = text("SELECT question_id, case_id, stem FROM questions WHERE stem ILIKE '%Horizonte%'")
        result = db.execute(query).fetchall()
        print(f"Found {len(result)} questions with 'Horizonte'")
        for row in result:
            print(f"Q_ID: {row[0]}, Case_ID: {row[1]}, Stem: {row[2][:50]}...")
            
            # Find the case if possible
            if row[1]:
                case_q = text("SELECT id, title FROM case_studies WHERE id = :case_id")
                case_row = db.execute(case_q, {"case_id": row[1]}).fetchone()
                if case_row:
                    print(f"  Linked to Case ID: {case_row[0]}, Title: '{case_row[1]}'")
                else:
                    print(f"  Linked to Case ID: {row[1]} (CASE NOT FOUND IN DB!)")
    finally:
        db.close()

if __name__ == "__main__":
    search_questions_for_horizonte()
