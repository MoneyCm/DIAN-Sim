import sqlite3
import os
import sys

db_path = os.path.abspath("dian_sim.db")
print(f"🔧 Force-Fixing Database at: {db_path}")

try:
    # Ensure writable
    if not os.access(db_path, os.W_OK):
        print("❌ DB is still read-only according to Python `os.access` check.")
        # Attempt chmod (unix style, might work on Windows partly)
        os.chmod(db_path, 0o777)
    
    conn = sqlite3.connect(db_path, timeout=30)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(user_stats)")
    columns_info = cursor.fetchall()
    existing_cols = [col[1] for col in columns_info]
    print(f"Current cols: {existing_cols}")
    
    if "last_ia_date" not in existing_cols:
        try:
            cursor.execute("ALTER TABLE user_stats ADD COLUMN last_ia_date TIMESTAMP")
            print("✅ Added: last_ia_date")
        except Exception as e:
            print(f"⚠️ Error adding last_ia_date: {e}")

    if "ia_count_today" not in existing_cols:
        try:
            cursor.execute("ALTER TABLE user_stats ADD COLUMN ia_count_today INTEGER DEFAULT 0")
            print("✅ Added: ia_count_today")
        except Exception as e:
            print(f"⚠️ Error adding ia_count_today: {e}")

    conn.commit()
    conn.close()
    print("🏁 Fix completed.")

except Exception as e:
    print(f"🔥 Critical Error: {e}")
