import sqlite3

db_path = 'dian_sim.db'

def cleanup_non_goa():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- CLEANUP: STRICT GOA COMPLIANCE (Deleting Non-Situational) ---")
    
    # Pre-count
    cursor.execute("SELECT COUNT(*) FROM questions")
    start_count = cursor.fetchone()[0]
    
    # Delete non-SITUACIÓN
    cursor.execute("DELETE FROM questions WHERE stem NOT LIKE '%SITUACIÓN%'")
    deleted = cursor.rowcount
    conn.commit()
    
    print(f"Deleted Rows: {deleted}")
    
    # Post-count
    cursor.execute("SELECT COUNT(*) FROM questions")
    end_count = cursor.fetchone()[0]
    print(f"Final Count: {end_count}")
    
    if end_count == start_count - deleted:
         print("Verification: OK")
    else:
         print("Verification: MISMATCH")

    conn.close()

if __name__ == "__main__":
    cleanup_non_goa()
