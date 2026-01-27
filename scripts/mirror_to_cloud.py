import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import Base, Question

def mirror():
    # 1. Setup Local Source
    local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dian_sim.db"))
    local_url = f"sqlite:///{local_path}"
    local_engine = create_engine(local_url)
    LocalSession = sessionmaker(bind=local_engine)
    local_db = LocalSession()

    # 2. Setup Cloud Destination
    from dotenv import load_dotenv
    load_dotenv()
    
    cloud_url = os.getenv("DATABASE_URL")
    
    if not cloud_url:
        try:
            import streamlit as st
            cloud_url = st.secrets.get("DATABASE_URL")
        except:
            pass

    if not cloud_url or "postgresql" not in cloud_url:
        print("Error: DATABASE_URL not set in .env or streamlit secrets, or not a PostgreSQL URL.")
        return

    if cloud_url.startswith("postgresql://"):
        cloud_url = cloud_url.replace("postgresql://", "postgresql+psycopg2://")
    
    cloud_engine = create_engine(cloud_url)
    CloudSession = sessionmaker(bind=cloud_engine)
    cloud_db = CloudSession()

    print(f"--- ATENCION: Iniciando Mirroring LOCAL -> CLOUD ---")
    
    # Count local questions
    try:
        local_count = local_db.query(Question).count()
        print(f"Preguntas Locales Detectadas: {local_count}")
    except Exception as e:
        print(f"Error leyendo DB local: {e}")
        return

    if local_count == 0:
        print("Error: La base de datos local esta vacia. No se realizara el mirroring para proteger la nube.")
        return

    # Deletion process
    try:
        # 3. Clear Cloud Questions (and dependencies)
        print("Limpiando preguntas en la Nube (borrando todo)...")
        # Delete dependencies first due to Foreign Keys
        from db.models import Attempt, QuestionPerformance
        cloud_db.query(Attempt).delete()
        cloud_db.query(QuestionPerformance).delete()
        cloud_db.query(Question).delete()
        cloud_db.commit()
        
        # 4. Upload Local Questions
        print(f"Subiendo {local_count} preguntas a la Nube...")
        local_questions = local_db.query(Question).all()
        for q in local_questions:
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
            cloud_db.add(new_q)
        
        cloud_db.commit()
        print(f"Exito! Mirroring completado. La Nube ahora tiene las mismas {local_count} preguntas.")
        
    except Exception as e:
        cloud_db.rollback()
        print(f"Error durante el mirroring: {e}")

    local_db.close()
    cloud_db.close()

if __name__ == "__main__":
    mirror()
