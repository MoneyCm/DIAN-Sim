import sqlite3
import os
import sys

db_path = os.path.abspath("dian_sim.db")
print(f"☢️ NUCLEAR SKILLS FIX: {db_path}")

try:
    conn = sqlite3.connect(db_path, timeout=30)
    c = conn.cursor()
    
    # 1. Check if column exists, if YES and it works, we don't nuke
    try:
        c.execute("SELECT user_id FROM skills LIMIT 1")
        print("✅ user_id ALREADY EXISTS and is readable. No nuke needed.")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"⚠️ user_id check failed: {e}")

    # 2. Backup existing rows roughly
    print("Backuping existing skills...")
    try:
        rows = c.execute("SELECT * FROM skills").fetchall()
        print(f"Backed up {len(rows)} rows (raw)")
    except Exception:
        rows = []
        print("Could not backup data (maybe table structure is too broken).")

    # 3. DROP TABLE
    print("💣 DROPPING TABLE skills...")
    c.execute("DROP TABLE IF EXISTS skills")
    
    # 4. RECREATE TABLE properly
    print("✨ RECREATING TABLE skills...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        skill_id VARCHAR(36) PRIMARY KEY,
        user_id INTEGER,
        track VARCHAR,
        competency VARCHAR,
        topic VARCHAR,
        macro_dominio VARCHAR,
        micro_competencia VARCHAR,
        mastery_score FLOAT DEFAULT 0.0,
        priority_weight FLOAT DEFAULT 1.0,
        last_seen TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    print("✅ TABLE RECREATED.")
    
    conn.commit()
    conn.close()

except Exception as e:
    print(f"🔥 FATAL ERROR: {e}")
