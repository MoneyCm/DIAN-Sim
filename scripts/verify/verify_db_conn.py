import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.session import DATABASE_URL, engine

print(f"--- 🛰️ ACTUAL DATABASE CONNECTION ---")
print(f"URL: {DATABASE_URL}")
print(f"Engine: {engine.url}")

# Check if we can connect and what's there
from sqlalchemy import text
try:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT count(*) FROM case_studies")).scalar()
        print(f"Cases count: {res}")
        
        # Check for Horizonte specifically
        terms = ['Horizonte', 'CNSC', 'San Vicente']
        for t in terms:
            c = conn.execute(text(f"SELECT count(*) FROM case_studies WHERE text ILIKE :t OR title ILIKE :t"), {"t": f"%{t}%"}).scalar()
            print(f"Cases with '{t}': {c}")
except Exception as e:
    print(f"Connection Error: {e}")
