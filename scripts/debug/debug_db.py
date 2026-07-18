from db.session import SessionLocal
from db.models import User, UserOPEC

def check_db():
    db = SessionLocal()
    print("-" * 50)
    print("USERS:")
    users = db.query(User).all()
    for u in users:
        print(f"ID: {u.id} | Name: {u.username}")
    
    print("-" * 50)
    print("OPECS:")
    opecs = db.query(UserOPEC).all()
    for o in opecs:
        print(f"ID: {o.id} | UserID: {o.user_id} | Num: {o.opec_number} | Active: {o.is_active}")
    print("-" * 50)
    db.close()

if __name__ == "__main__":
    check_db()
