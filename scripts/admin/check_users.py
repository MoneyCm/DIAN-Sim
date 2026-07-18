import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if url and url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg2://", 1)

if not url:
    print("No DATABASE_URL found")
    exit()

engine = create_engine(url)
with engine.connect() as conn:
    print("--- USERS ---")
    users = conn.execute(text("SELECT id, username, email FROM users")).fetchall()
    for u in users:
        print(f"ID: {u[0]} | User: {u[1]} | Email: {u[2]}")
    
    print("\n--- OPECs ---")
    opecs = conn.execute(text("SELECT user_id, opec_number, job_title FROM user_opec")).fetchall()
    for o in opecs:
        print(f"UserID: {o[0]} | OPEC: {o[1]} | Title: {o[2]}")
