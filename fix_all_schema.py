import sqlite3
import os
import sys

db_path = os.path.abspath("dian_sim.db")
print(f"🔧 [FIX-ALL] Database at: {db_path}")

# Definition of ALL new columns we expect (table, column, definition)
# Extracted from db/session.py sync_db_schema
EXPECTED_COLS = [
    # user_stats
    ("user_stats", "last_ia_date", "TIMESTAMP"),
    ("user_stats", "ia_count_today", "INTEGER DEFAULT 0"),
    # question_performance
    ("question_performance", "mastery_level", "FLOAT"),
    ("question_performance", "is_mastered", "BOOLEAN"),
    ("question_performance", "is_favorite", "BOOLEAN DEFAULT FALSE"), # The one crashing dashboard now
    # questions
    ("questions", "macro_dominio", "VARCHAR"),
    ("questions", "micro_competencia", "VARCHAR"),
    ("questions", "is_verified", "BOOLEAN DEFAULT FALSE"),
    ("questions", "quality_report", "JSON"),
    ("questions", "global_hits", "INTEGER DEFAULT 0"),
    ("questions", "global_misses", "INTEGER DEFAULT 0"),
    ("questions", "case_id", "VARCHAR"),
    ("questions", "question_type", "VARCHAR DEFAULT 'SITUATIONAL'"),
    # skills
    ("skills", "macro_dominio", "VARCHAR"),
    ("skills", "micro_competencia", "VARCHAR"),
    ("skills", "priority_weight", "FLOAT"),
    ("skills", "last_seen", "TIMESTAMP"),
    # users
    ("users", "subscription_tier", "VARCHAR DEFAULT 'free'"),
    ("users", "subscription_expiry", "TIMESTAMP"),
    ("users", "stripe_customer_id", "VARCHAR")
]

try:
    if os.path.exists(db_path):
        # Force writeable if needed (chmod)
        try:
             os.chmod(db_path, 0o777)
        except: pass
        
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        for table, col_name, definition in EXPECTED_COLS:
            # Check if table exists first
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                print(f"⚠️ Table '{table}' does not exist, skipping col '{col_name}'")
                continue
                
            # Check if col exists
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [info[1] for info in cursor.fetchall()]
            
            if col_name not in cols:
                print(f"🔨 Adding missing col: {table}.{col_name}...")
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {definition}")
                    print(f"   ✅ Added {col_name}")
                except Exception as e:
                    print(f"   ❌ Failed to add {col_name}: {e}")
            else:
                # print(f"   ok: {table}.{col_name}")
                pass
                
        conn.commit()
        conn.close()
        print("🏁 All schema checks finished.")
    else:
        print("❌ DB file not found.")

except Exception as e:
    print(f"🔥 Critical Error: {e}")
