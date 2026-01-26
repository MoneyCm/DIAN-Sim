import sys
import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import Base, Question, Attempt, Skill

def migrate():
    # 1. Setup Source (SQLite)
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dian_sim.db"))
    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(sqlite_url)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_db = SqliteSession()

    # 2. Setup Destination (PostgreSQL)
    from dotenv import load_dotenv
    load_dotenv()
    pg_url = os.getenv("DATABASE_URL")
    if not pg_url or "postgresql" not in pg_url:
        print("Error: DATABASE_URL not set or not a PostgreSQL URL.")
        return

    if pg_url.startswith("postgresql://"):
        pg_url = pg_url.replace("postgresql://", "postgresql+psycopg2://")
    
    pg_engine = create_engine(pg_url)
    PgSession = sessionmaker(bind=pg_engine)
    pg_db = PgSession()

    print(f"Connecting to Cloud DB: {pg_url.split('@')[1]}") # Log host safely

    # 3. Create Tables in Cloud
    print("Creating tables in cloud...")
    Base.metadata.create_all(bind=pg_engine)

    # 4. Migrate Questions
    print("Migrating Questions...")
    questions = sqlite_db.query(Question).all()
    count_q = 0
    for q in questions:
        # Check if already exists by hash
        exists = pg_db.query(Question).filter_by(hash_norm=q.hash_norm).first()
        if not exists:
            # Create a new instance to avoid session conflicts
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
                hash_norm=q.hash_norm
            )
            pg_db.add(new_q)
            count_q += 1
    
    pg_db.commit()
    print(f"Migrated {count_q} new questions.")

    # 5. Migrate Skills
    print("Migrating Skills/Mastery...")
    skills = sqlite_db.query(Skill).all()
    count_s = 0
    for s in skills:
        exists = pg_db.query(Skill).filter_by(track=s.track, competency=s.competency, topic=s.topic).first()
        if not exists:
            new_s = Skill(
                skill_id=s.skill_id,
                track=s.track,
                competency=s.competency,
                topic=s.topic,
                mastery_score=s.mastery_score,
                priority_weight=s.priority_weight,
                last_seen=s.last_seen,
                updated_at=s.updated_at
            )
            pg_db.add(new_s)
            count_s += 1
    pg_db.commit()
    print(f"Migrated {count_s} skill profiles.")

    # 6. Migrate Attempts
    print("Migrating Attempts...")
    attempts = sqlite_db.query(Attempt).all()
    count_a = 0
    for a in attempts:
        exists = pg_db.query(Attempt).filter_by(attempt_id=a.attempt_id).first()
        if not exists:
            new_a = Attempt(
                attempt_id=a.attempt_id,
                question_id=a.question_id,
                created_at=a.created_at,
                chosen_key=a.chosen_key,
                is_correct=a.is_correct,
                time_sec=a.time_sec,
                confidence_1_5=a.confidence_1_5,
                error_tag=a.error_tag,
                notes=a.notes
            )
            pg_db.add(new_a)
            count_a += 1
    pg_db.commit()
    print(f"Migrated {count_a} attempt history items.")

    print("Migration finished successfully! 🚀")
    
    sqlite_db.close()
    pg_db.close()

if __name__ == "__main__":
    migrate()
