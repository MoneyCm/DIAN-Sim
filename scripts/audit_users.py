
import sys
import os
from sqlalchemy import func

# Add project root to path
sys.path.append(os.getcwd())

from db.session import SessionLocal
from db.models import User, UserOPEC

def audit():
    db = SessionLocal()
    users = db.query(User).all()
    print(f"👥 Total Usuarios: {len(users)}")
    
    for u in users:
        print(f"\n👤 ID: {u.id} | User: {u.username} | Email: {u.email}")
        opecs = db.query(UserOPEC).filter_by(user_id=u.id).all()
        for o in opecs:
            status = "✅ ACTIVA" if o.is_active else "⚪"
            print(f"   - [{status}] ID: {o.id} | Titulo: {o.job_title} | Num: '{o.opec_number}'")
            
    db.close()

if __name__ == "__main__":
    audit()
