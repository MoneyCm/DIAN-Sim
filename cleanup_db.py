import sqlite3
import os

db_path = 'dian_sim.db'

def cleanup():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- STARTING CLEANUP ---")
    
    # 1. Verify Start Count
    cursor.execute("SELECT COUNT(*) FROM questions")
    start_count = cursor.fetchone()[0]
    print(f"Starting Count: {start_count}")

    # 2. Execute Deletion
    # Logic: Delete if NOT Gestor II AND NOT GOA (SITUACIÓN)
    query = """
    DELETE FROM questions 
    WHERE (topic NOT LIKE '%Gestor II%' AND competency NOT LIKE '%Gestor II%')
    AND NOT (stem LIKE 'SITUACIÓN%' OR stem LIKE '%SITUACIÓN%');
    """
    cursor.execute(query)
    deleted_count = cursor.rowcount
    conn.commit()
    
    print(f"Deleted Rows: {deleted_count}")

    # 3. Verify End Count
    cursor.execute("SELECT COUNT(*) FROM questions")
    end_count = cursor.fetchone()[0]
    print(f"Final Count: {end_count}")
    
    conn.close()

if __name__ == "__main__":
    cleanup()
