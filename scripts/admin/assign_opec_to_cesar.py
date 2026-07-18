
import sys
import os
from sqlalchemy import func

# Add project root to path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from db.models import User, UserOPEC

def assign():
    db = SessionLocal()
    
    # 1. Get Cesar
    cesar = db.query(User).filter(User.username.ilike("cesar")).first()
    if not cesar:
        print("❌ Usuario 'cesar' no encontrado.")
        return

    print(f"👤 Usuario encontrado: {cesar.username} (ID: {cesar.id})")
    
    # 2. Deactivate current active
    active = db.query(UserOPEC).filter_by(user_id=cesar.id, is_active=True).first()
    if active:
        active.is_active = False
        print(f"📉 Desactivada OPEC anterior: {active.job_title}")
        
    # 3. Check if he already has 236739
    target = db.query(UserOPEC).filter_by(user_id=cesar.id, opec_number="236739").first()
    
    if target:
        target.is_active = True
        print(f"✅ OPEC 236739 reactivada para {cesar.username}.")
    else:
        # Create it
        print(f"✨ Creando OPEC 236739 para {cesar.username}...")
        new_opec = UserOPEC(
            user_id=cesar.id,
            opec_number="236739",
            job_title="OPEC 236739 - Gestor III",
            level="Profesional",
            purpose="Corrección masiva - Asignación directa.",
            functions=[],
            is_active=True
        )
        db.add(new_opec)
        print("✅ OPEC creada y activada.")
        
    db.commit()
    db.close()

if __name__ == "__main__":
    assign()
