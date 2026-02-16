import os, sys
from db.session import SessionLocal
from db.models import Question, UserOPEC
from services.question_service import QuestionService

def count_questions():
    db = SessionLocal()
    # Assumption: User ID is 2 based on previous logs. If not sure, we can select first user with OPEC.
    # But let's verify if there is a way to get the "current" user, likely from a session logic or just grab the first one.
    # The previous conversations showed user_id=2 in the error logs ("parameters: (2,)").
    target_user_id = 2 
    
    try:
        user_opec = db.query(UserOPEC).filter_by(user_id=target_user_id, is_active=True).first()
        if not user_opec:
            print("❌ No active OPEC found for user_id=2.")
            return

        print(f"👤 User: {target_user_id}")
        print(f"🎯 Active OPEC: {user_opec.opec_number} - {user_opec.job_title}")
        
        # 1. Total Raw
        total_questions = db.query(Question).count()
        print(f"\n📚 Total Questions in DB: {total_questions}")
        
        # 2. Strict OPEC Match
        strict_matches = db.query(Question).filter(Question.topic.contains(user_opec.opec_number)).count()
        print(f"💎 Specific for OPEC {user_opec.opec_number}: {strict_matches}")
        
        # 3. Filtered Pool (using service logic)
        filtered_questions = QuestionService.get_questions_for_user(db, target_user_id)
        print(f"✅ Available for you (Filtered Pool): {len(filtered_questions)}")
        
        # Breakdown of filtered pool
        topics = {}
        for q in filtered_questions:
            topics[q.track] = topics.get(q.track, 0) + 1
            
        print("\n📊 Breakdown by Track:")
        for t, c in topics.items():
            print(f"   - {t}: {c}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    count_questions()
