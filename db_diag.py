
import os, sys
PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import SessionLocal
from db.models import User, Question, Attempt, Skill, QuestionPerformance
from sqlalchemy import func

def run_diagnostic():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}\n")
        
        for user in users:
            print(f"--- User: {user.username} (ID: {user.id}) ---")
            
            # 1. Total attempts and performance
            total_attempts = db.query(Attempt).filter_by(user_id=user.id).count()
            print(f"Total Attempts: {total_attempts}")
            
            # 2. Questions with performance entries (seen questions)
            q_perf = db.query(Question.track, func.count(Question.question_id))\
                       .join(QuestionPerformance, Question.question_id == QuestionPerformance.question_id)\
                       .filter(QuestionPerformance.user_id == user.id)\
                       .group_by(Question.track).all()
            
            print("Questions with performance data (by Track):")
            if not q_perf:
                print("  None")
            for track, count in q_perf:
                print(f"  - {track}: {count} questions")
            
            # 3. Topics (Top 5)
            q_topics = db.query(Question.topic, func.count(Question.question_id))\
                         .join(QuestionPerformance, Question.question_id == QuestionPerformance.question_id)\
                         .filter(QuestionPerformance.user_id == user.id)\
                         .group_by(Question.topic)\
                         .order_by(func.count(Question.question_id).desc())\
                         .limit(5).all()
            
            print("Top Topics seen:")
            for topic, count in q_topics:
                print(f"  - {topic}: {count}")
            
            # 4. Mastery from Skills table
            skills = db.query(Skill).filter_by(user_id=user.id).all()
            print(f"Skills Profile Size: {len(skills)} topics tracked.")
            
            print("-" * 40)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_diagnostic()
