
import sys
import os
from sqlalchemy import func

# Add project root to path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from db.models import Question

def view():
    db = SessionLocal()
    qs = db.query(Question).filter(Question.topic.ilike("%GESTOR IV%")).limit(3).all()
    for q in qs:
        print(f"ID: {q.question_id}")
        print(f"Topic: {q.topic}")
        print(f"Track: {q.track}")
        print("-" * 50)
    db.close()

if __name__ == "__main__":
    view()
