
import sys
import os
from sqlalchemy import func

# Add project root to path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from db.models import UserOPEC, Question

def check():
    db = SessionLocal()
    
    # 1. Active OPEC
    active = db.query(UserOPEC).filter_by(is_active=True).first()
    if active:
        print(f"🎯 OPEC ACTIVA: {active.job_title} (ID: {active.id})")
        print(f"   - Functions: {str(active.functions)[:100]}...")
    else:
        print("⚠️ NO HAY OPEC ACTIVA.")

    # 2. Check for OPEC 236739
    target = db.query(UserOPEC).filter(UserOPEC.job_title.ilike("%236739%")).first()
    if target:
        print(f"✅ OPEC 236739 encontrada: {target.job_title} (ID: {target.id})")
    else:
        print("❌ OPEC 236739 NO encontrada en BD.")

    # 3. Check recent questions (Gestor IV)
    count_g4 = db.query(Question).filter(Question.topic.ilike("%GESTOR IV%")).count()
    print(f"📊 Preguntas 'GESTOR IV': {count_g4}")

    db.close()

if __name__ == "__main__":
    check()
