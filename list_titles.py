
import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
from db.session import SessionLocal

def list_all_titles():
    db = SessionLocal()
    try:
        query = text("SELECT title FROM case_studies")
        result = db.execute(query).fetchall()
        print(f"Total cases: {len(result)}")
        for i, row in enumerate(result):
            print(f"{i+1:2d}. {row[0]}")
    finally:
        db.close()

if __name__ == "__main__":
    list_all_titles()
