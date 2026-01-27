import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import Base, Question, Skill, UserStats, Achievement

def sync():
    # 1. Setup Destination (Local SQLite)
    local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dian_sim.db"))
    local_url = f"sqlite:///{local_path}"
    local_engine = create_engine(local_url)
    LocalSession = sessionmaker(bind=local_engine)
    local_db = LocalSession()

    # 2. Setup Source (Cloud PostgreSQL)
    from dotenv import load_dotenv
    load_dotenv()
    cloud_url = os.getenv("DATABASE_URL")
    if not cloud_url or "postgresql" not in cloud_url:
        print("Error: DATABASE_URL not set in .env or not a PostgreSQL URL.")
        print("Required for Cloud connection.")
        return

    if cloud_url.startswith("postgresql://"):
        cloud_url = cloud_url.replace("postgresql://", "postgresql+psycopg2://")
    
    cloud_engine = create_engine(cloud_url)
    CloudSession = sessionmaker(bind=cloud_engine)
    cloud_db = CloudSession()

    print(f"Connecting to Cloud DB to PULL data...")

    # 3. Ensure Local Tables Exist
    Base.metadata.create_all(bind=local_engine)

    # 4. Sync Questions
    print("Syncing Questions from Cloud to Local...")
    cloud_questions = cloud_db.query(Question).all()
    count_q = 0
    for q in cloud_questions:
        exists = local_db.query(Question).filter_by(hash_norm=q.hash_norm).first()
        if not exists:
            # Create a new instance for local
            new_q = Question(
                question_id=q.question_id,
                track=q.track,
                competency=q.competency,
                topic=q.topic,
                difficulty=q.difficulty,
                stem=q.stem,
                options_json=q.options_json,
                correct_key=q.correct_key,
                rationale=q.rationale,
                source_refs=q.source_refs,
                created_at=q.created_at,
                hash_norm=q.hash_norm,
                is_verified=q.is_verified,
                quality_report=q.quality_report,
                macro_dominio=q.macro_dominio,
                micro_competencia=q.micro_competencia
            )
            local_db.add(new_q)
            count_q += 1
    
    local_db.commit()
    print(f"Synced {count_q} new questions to local database.")

    # 5. Optional: Sync other tables? 
    # For now, let's keep it to questions as requested.

    local_db.close()
    cloud_db.close()
    print("Optimization: Local database is now updated! 🚀")

if __name__ == "__main__":
    sync()
