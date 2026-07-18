from db.session import SessionLocal
from db.models import Question

def check_count():
    db = SessionLocal()
    try:
        count = db.query(Question).count()
        print(f"Total Questions: {count}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_count()
