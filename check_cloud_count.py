import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add current dir to path to import models
sys.path.append(os.getcwd())
from db.models import Question

def check_cloud():
    # New ID from User
    project_id = "ejvpdzgnkstkljgwktfj"
    password = "27UmC7ZGqh9t.bL"
    
    variations = [
        # User provided format
        f"postgresql+psycopg2://postgres:{password}@db.{project_id}.supabase.co:5432/postgres",
        # Pooler format
        f"postgresql+psycopg2://postgres.{project_id}:{password}@aws-1-us-east-1.pooler.supabase.com:5432/postgres",
        # Pooler Transaction Mode (Port 6543)
        f"postgresql+psycopg2://postgres.{project_id}:{password}@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
    ]
    
    for url in variations:
        print(f"Trying: {url.split('@')[-1]}")
        try:
            engine = create_engine(url, connect_args={'connect_timeout': 5})
            Session = sessionmaker(bind=engine)
            db = Session()
            count = db.query(Question).count()
            print(f"SUCCESS! Count: {count}")
            db.close()
            # Update .env if successful
            return url
        except Exception as e:
            print(f"Failed: {str(e)[:100]}...")
    return None

if __name__ == "__main__":
    check_cloud()
