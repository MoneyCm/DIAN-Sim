import sqlite3
import bcrypt
from db.models import User, Question
from db.session import SessionLocal
from core.auth import AuthManager
from services.question_service import QuestionService

def debug_system():
    db = SessionLocal()
    print("--- DEBUGGING AUTH & FILTER ---")

    # 1. Check Users
    print("\n[USERS TABLE]")
    users = db.query(User).all()
    for u in users:
        print(f"ID: {u.id} | User: {u.username} | Role: {u.role} | Hash: {u.password_hash[:10]}...")

    # 2. Test Admin Login
    print("\n[TESTING ADMIN LOGIN]")
    admin = db.query(User).filter(User.username == 'admin').first()
    if admin:
        input_pass = "1234"
        is_valid = False
        try:
            # Replicate AuthManager.verify_password logic
            is_valid = bcrypt.checkpw(input_pass.encode(), admin.password_hash.encode())
        except Exception as e:
            print(f"Bcrypt Error: {e}")
        
        print(f"Login 'admin'/'1234': {'SUCCESS' if is_valid else 'FAILED'}")
    else:
        print("Admin user not found.")

    # 3. Test Cesar Filter (Why 0?)
    print("\n[TESTING CESAR FILTER]")
    cesar = db.query(User).filter(User.username == 'cesar').first()
    if cesar:
        # Check raw count
        total = db.query(Question).count()
        print(f"Total Questions in DB: {total}")
        
        # Check Service
        q_filtered = QuestionService.get_questions_for_user(db, cesar.id)
        print(f"Filtered for Cesar: {len(q_filtered)}")
        
        if len(q_filtered) == 0:
            print("  -> Debugging Filter constraints...")
            # Check why?
            # A. Matches OPEC?
            from db.models import UserOPEC
            u_opec = db.query(UserOPEC).filter_by(user_id=cesar.id).first()
            print(f"  User OPEC: {u_opec.opec_number if u_opec else 'None'}")
            
            # B. Customs Filter
            q_no_customs = db.query(Question).filter(
                ~Question.topic.ilike('%Aduan%')
            ).count()
            print(f"  Non-Customs Count: {q_no_customs}")
            
            # C. Situational Filter
            q_situational = db.query(Question).filter(
                Question.stem.ilike('%SITUACIÓN%')
            ).count()
            print(f"  Situational Count: {q_situational}")

    db.close()

if __name__ == "__main__":
    debug_system()
