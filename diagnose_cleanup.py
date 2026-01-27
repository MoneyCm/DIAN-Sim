import sqlite3
import os

db_path = 'dian_sim.db'

def diagnose():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Total questions
    cursor.execute("SELECT COUNT(*) FROM questions")
    total = cursor.fetchone()[0]
    print(f"Total Questions: {total}")

    # 2. Gestor II questions (Topic or Competency)
    cursor.execute("SELECT COUNT(*) FROM questions WHERE topic LIKE '%Gestor II%' OR competency LIKE '%Gestor II%'")
    gestor_ii = cursor.fetchone()[0]
    print(f"Gestor II Questions (LIKE %Gestor II%): {gestor_ii}")

    # 3. Questions with GOA markers (SITUACIÓN)
    cursor.execute("SELECT COUNT(*) FROM questions WHERE stem LIKE 'SITUACIÓN%' OR stem LIKE '%SITUACIÓN%'")
    goa_marks = cursor.fetchone()[0]
    print(f"Questions with 'SITUACIÓN' in stem: {goa_marks}")

    # 4. Questions to DELETE:
    # (NOT Gestor II) AND (NOT SITUACIÓN)
    cursor.execute("""
        SELECT COUNT(*) FROM questions 
        WHERE (topic NOT LIKE '%Gestor II%' AND competency NOT LIKE '%Gestor II%')
        AND NOT (stem LIKE 'SITUACIÓN%' OR stem LIKE '%SITUACIÓN%')
    """)
    to_delete = cursor.fetchone()[0]
    print(f"Questions to Delete: {to_delete}")

    # 5. Kept list count
    cursor.execute("""
        SELECT COUNT(*) FROM questions 
        WHERE (topic LIKE '%Gestor II%' OR competency LIKE '%Gestor II%')
        OR (stem LIKE 'SITUACIÓN%' OR stem LIKE '%SITUACIÓN%')
    """)
    to_keep = cursor.fetchone()[0]
    print(f"Questions to Keep: {to_keep}")

    # 5. Sample of what would be kept but is NOT Gestor II (should be GOA)
    cursor.execute("""
        SELECT competency, topic, source_refs FROM questions 
        WHERE (topic != 'Gestor II' AND competency != 'Gestor II')
        AND (source_refs LIKE '%GOA%' OR rationale LIKE '%GOA%' OR stem LIKE '%GOA%' OR source_refs LIKE '%2667%' OR rationale LIKE '%2667%' OR stem LIKE '%2667%')
        LIMIT 5
    """)
    kept_non_gestor = cursor.fetchall()
    print("\nSample Kept (Non-Gestor II, but GOA):")
    for r in kept_non_gestor:
        print(f"  C: {r[0]} | T: {r[1]} | R: {r[2]}")

    # 6. Sample of what would be Deleted
    cursor.execute("""
        SELECT competency, topic, source_refs FROM questions 
        WHERE (topic != 'Gestor II' AND competency != 'Gestor II')
        AND NOT (source_refs LIKE '%GOA%' OR rationale LIKE '%GOA%' OR stem LIKE '%GOA%' OR source_refs LIKE '%2667%' OR rationale LIKE '%2667%' OR stem LIKE '%2667%')
        LIMIT 5
    """)
    deleted_sample = cursor.fetchall()
    print("\nSample to Delete:")
    for r in deleted_sample:
        print(f"  C: {r[0]} | T: {r[1]} | R: {r[2]}")

    conn.close()

if __name__ == "__main__":
    diagnose()
