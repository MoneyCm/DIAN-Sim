import sqlite3
import os

db_path = os.path.abspath("dian_sim.db")
print(f"Checking DB: {db_path}")

if not os.path.exists(db_path):
    print("❌ DB File not found!")
    exit()

conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    c.execute("PRAGMA table_info(skills)")
    rows = c.fetchall()
    print("Skills Table Columns:")
    found_user_id = False
    for r in rows:
        print(f" - {r[1]} ({r[2]})")
        if r[1] == 'user_id':
            found_user_id = True
            
    if not found_user_id:
        print("❌ 'user_id' MISSING in skills table.")
        print("Attempting fix...")
        try:
            c.execute("ALTER TABLE skills ADD COLUMN user_id INTEGER")
            conn.commit()
            print("✅ 'user_id' added successfully.")
        except Exception as e:
            print(f"❌ Failed to add column: {e}")
    else:
        print("✅ 'user_id' exists.")
        
except Exception as e:
    print(f"❌ Error inspecting skills: {e}")

conn.close()
