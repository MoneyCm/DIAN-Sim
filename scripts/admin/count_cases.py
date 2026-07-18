import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM case_studies WHERE topic LIKE '%236769%'"))
        count = result.scalar()
        print(f"COUNT_RESULT:{count}")
except Exception as e:
    print(f"Error: {e}")
