import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from db.session import SessionLocal, engine
from db.models import Question, Base
from core.generators.templates import generate_dummy_questions

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_data(db: Session):
    existing = db.query(Question).count()
    if existing > 0:
        print(f"Database already has {existing} questions. Skipping seed.")
        return

    print("Generating seed questions...")
    # Generate more than needed to account for duplicates being removed
    data = generate_dummy_questions(count=300)
    
    objects = []
    seen_hashes = set()
    
    for item in data:
        if item["hash_norm"] in seen_hashes:
            continue
            
        seen_hashes.add(item["hash_norm"])
        
        # Pydantic validation could go here, but direct mapping is faster for seed
        q = Question(**item)
        objects.append(q)
        
        if len(objects) >= 200:
            break
    
    db.add_all(objects)
    db.commit()
    print(f"Seeded {len(objects)} questions.")

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    seed_data(db)
    db.close()
