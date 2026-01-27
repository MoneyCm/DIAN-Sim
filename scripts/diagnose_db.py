import sys
import os

# Set working directory to project root
os.chdir(r'C:\Proyectos\DIAN-Sim')
sys.path.append(r'C:\Proyectos\DIAN-Sim')

from db.session import DATABASE_URL, Question
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

print(f"DATABASE_URL: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

count = db.query(Question).count()
print(f"Question Count: {count}")

# Print first 5 topics
topics = db.query(Question.topic).distinct().all()
print(f"Topics: {[t[0] for t in topics]}")

db.close()
