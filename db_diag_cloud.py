
import os, sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

from db.session import SessionLocal
from db.models import User, Question, Attempt, QuestionPerformance
from sqlalchemy import func

def run_cloud_diag():
    db = SessionLocal()
    try:
        url = os.getenv("DATABASE_URL", "Unknown")
        print(f"Connected to: {url[:30]}...\n")
        
        users = db.query(User).all()
        print(f"Total Users in Cloud: {len(users)}\n")
        
        # Total Questions
        total_q = db.query(Question).count()
        print(f"Total Questions in Cloud Bank: {total_q}\n")

        for user in users:
            print(f"--- User: {user.username} (ID: {user.id}) ---")
            
            # 1. Total attempts
            total_attempts = db.query(Attempt).filter_by(user_id=user.id).count()
            print(f"Total Attempts (Responses): {total_attempts}")
            
            # 2. Tracks distribution (Seen)
            q_perf = db.query(Question.track, func.count(Question.question_id))\
                       .join(QuestionPerformance, Question.question_id == QuestionPerformance.question_id)\
                       .filter(QuestionPerformance.user_id == user.id)\
                       .group_by(Question.track).all()
            
            print("Questions Answered (by Track):")
            if not q_perf:
                print("  None")
            for track, count in q_perf:
                print(f"  - {track}: {count}")
            
            # 3. Last activity
            last_att = db.query(Attempt.created_at)\
                         .filter_by(user_id=user.id)\
                         .order_by(Attempt.created_at.desc())\
                         .first()
            if last_att:
                print(f"Last Activity: {last_att[0]}")
            else:
                print("Last Activity: Never")
            
            print("-" * 40)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_cloud_diag()
