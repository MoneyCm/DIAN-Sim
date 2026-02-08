
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.orm import Session
import pandas as pd

# Load env vars
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import SessionLocal
from db.models import Question

def get_db_summary():
    try:
        db: Session = SessionLocal()
        
        # Total count
        total_questions = db.query(Question).count()
        
        # Group by Topic
        results = db.query(
            Question.topic, 
            func.count(Question.question_id)
        ).group_by(Question.topic).order_by(func.count(Question.question_id).desc()).limit(20).all()
        
        print("\n### 📊 Resumen de Base de Datos")
        print(f"**Total General:** {total_questions} Preguntas\n")
        
        print("| Tema / Categoría | Cantidad | % del Total |")
        print("| :--- | :---: | :---: |")
        
        for topic, count in results:
            percentage = (count / total_questions) * 100 if total_questions > 0 else 0
            topic_clean = topic if topic else "General / Sin Clasificar"
            print(f"| {topic_clean} | {count} | {percentage:.1f}% |")
            
        db.close()
        
    except Exception as e:
        print(f"Error generando reporte: {e}")

if __name__ == "__main__":
    get_db_summary()
