from db.session import engine, DATABASE_URL
from sqlalchemy import text
import os

print(f"DATABASE_URL used: {DATABASE_URL}")
try:
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM questions")).scalar()
        print(f"Total Questions: {count}")
except Exception as e:
    print(f"Error: {e}")
