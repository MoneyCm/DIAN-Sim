import sqlite3
import os
import sys

db_path = os.path.abspath("dian_sim.db")
print(f"🔧 Fixing SKILLS table at: {db_path}")

try:
    # Force writeable
    try: os.chmod(db_path, 0o777)
    except: pass
    
    conn = sqlite3.connect(db_path, timeout=30)
    cursor = conn.cursor()
    
    # Check SKILLS columns
    cursor.execute("PRAGMA table_info(skills)")
    cols = [info[1] for info in cursor.fetchall()]
    print(f"Current skills cols: {cols}")
    
    # Fix user_id
    if "user_id" not in cols:
        print("🔨 Adding user_id to skills...")
        try:
            cursor.execute("ALTER TABLE skills ADD COLUMN user_id INTEGER")
            print("✅ Added user_id")
        except Exception as e:
            print(f"❌ Error adding user_id: {e}")
            
    # Check other potentially missing skills columns
    extra_cols = [
        ("macro_dominio", "VARCHAR"),
        ("micro_competencia", "VARCHAR"),
        ("priority_weight", "FLOAT DEFAULT 1.0"),
        ("last_seen", "TIMESTAMP")
    ]
    
    for col, definition in extra_cols:
        if col not in cols:
             print(f"🔨 Adding {col} to skills...")
             try:
                 cursor.execute(f"ALTER TABLE skills ADD COLUMN {col} {definition}")
                 print(f"✅ Added {col}")
             except Exception as e:
                 print(f"❌ Error adding {col}: {e}")

    conn.commit()
    conn.close()
    print("🏁 Skills fix completed.")

except Exception as e:
    print(f"🔥 Critical Error: {e}")
