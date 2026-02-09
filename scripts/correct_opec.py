
import sys
import os
import uuid
from sqlalchemy import func

# Add project root to path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from db.models import UserOPEC, Question, User

def correct():
    db = SessionLocal()
    
    # 1. Get User ID (Assuming single user or taking the one from existing active)
    active = db.query(UserOPEC).filter_by(is_active=True).first()
    if not active:
        # Fallback to first user
        u = db.query(User).first()
        if not u:
            print("❌ No use found.")
            return
        user_id = u.id
    else:
        user_id = active.user_id
        # Deactivate current
        active.is_active = False
        print(f"📉 Desactivada OPEC actual: {active.job_title}")

    # 2. Check if target OPEC exists
    target_title = "OPEC 236739 - Gestor III"
    target = db.query(UserOPEC).filter(UserOPEC.job_title.ilike("%236739%")).first()
    
    if not target:
        print(f"✨ Creando nueva OPEC: {target_title}")
        target = UserOPEC(
            user_id=user_id,
            opec_number="236739",
            job_title=target_title,
            level="Profesional", # Assumed based on Gestor III
            # grade="03", # Removed
            # code="301", # Removed 
            # manual_functions=... # Removed
            purpose="Corrección masiva de preguntas.",
            functions=[],
            is_active=True
        )
        db.add(target)
        db.commit() # Commit to get ID
        db.refresh(target)
    else:
        print(f"✅ OPEC destino encontrada: {target.job_title}")
        target.is_active = True
        
    print(f"🎯 OPEC Activa ahora es: {target.job_title}")

    # 3. Migrate Questions
    # Find questions with "GESTOR IV" inside
    qs = db.query(Question).filter(Question.topic.ilike("%GESTOR IV%")).all()
    print(f"📋 Encontradas {len(qs)} preguntas para migrar.")
    
    count = 0
    for q in qs:
        # Replace "GESTOR IV" with "OPEC 236739 - Gestor III"
        # Example: "GESTOR IV - Comportamental" -> "OPEC 236739 - Gestor III - Comportamental"
        new_topic = q.topic.upper().replace("GESTOR IV", "OPEC 236739 - Gestor III")
        if q.topic != new_topic:
            q.topic = new_topic
            count += 1
            
    db.commit()
    print(f"✅ Migradas {count} preguntas exitosamente.")
    db.close()

if __name__ == "__main__":
    correct()
