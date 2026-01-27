import sqlite3
import sys
import os

# Mock DB Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, User
from services.question_service import QuestionService

db_path = 'dian_sim.db'
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)
session = Session()

def verify():
    print("--- VERIFYING DYNAMIC FILTER ---")
    
    # 1. Get Cesar ID
    user_cesar = session.query(User).filter_by(username='cesar').first()
    if not user_cesar:
        print("User 'cesar' not found!")
        return
    
    # 2. Test Cesar View
    print(f"Testing View for User: {user_cesar.username} (ID: {user_cesar.id})")
    questions_cesar = QuestionService.get_questions_for_user(session, user_cesar.id)
    count_cesar = len(questions_cesar)
    print(f"Questions visible to Cesar: {count_cesar}")
    
    if count_cesar == 362:
         print("✅ MATCH: Cesar sees exactly 362 questions.")
    else:
         print(f"❌ MISMATCH: Expected 362, got {count_cesar}")

    # 3. Test Admin View (No User ID)
    print("\nTesting View for Admin (None)")
    questions_admin = QuestionService.get_questions_for_user(session, None)
    count_admin = len(questions_admin)
    print(f"Questions visible to Admin: {count_admin}")
    
    if count_admin == 955:
         print("✅ MATCH: Admin sees full database (955).")
    else:
         print(f"❌ MISMATCH: Expected 955, got {count_admin}")

    session.close()

if __name__ == "__main__":
    verify()
