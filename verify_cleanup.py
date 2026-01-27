import sqlite3

db_path = 'dian_sim.db'

def verify():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=== VERIFICATION REPORT ===\n")
    
    # 1. Total Count
    cursor.execute("SELECT COUNT(*) FROM questions")
    total = cursor.fetchone()[0]
    print(f"Total Questions: {total}")

    # 2. Gestor II Count
    cursor.execute("SELECT COUNT(*) FROM questions WHERE topic LIKE '%Gestor II%' OR competency LIKE '%Gestor II%'")
    gestor_ii = cursor.fetchone()[0]
    print(f"Gestor II Questions: {gestor_ii}")

    # 3. GOA (SITUACIÓN) Count
    cursor.execute("SELECT COUNT(*) FROM questions WHERE stem LIKE '%SITUACIÓN%'")
    goa = cursor.fetchone()[0]
    print(f"GOA Protocol Questions: {goa}")

    # 4. Sample of remaining questions
    print("\n=== SAMPLE OF REMAINING QUESTIONS ===")
    cursor.execute("SELECT competency, topic, SUBSTR(stem, 1, 60) FROM questions LIMIT 10")
    samples = cursor.fetchall()
    for i, s in enumerate(samples, 1):
        print(f"{i}. C: {s[0]} | T: {s[1]} | Stem: {s[2]}...")

    # 5. Verify no unwanted questions remain
    cursor.execute("""
        SELECT COUNT(*) FROM questions 
        WHERE (topic NOT LIKE '%Gestor II%' AND competency NOT LIKE '%Gestor II%')
        AND NOT (stem LIKE '%SITUACIÓN%')
    """)
    unwanted = cursor.fetchone()[0]
    print(f"\n=== QUALITY CHECK ===")
    print(f"Unwanted Questions Remaining: {unwanted}")
    
    if unwanted == 0:
        print("✅ CLEANUP SUCCESSFUL - All unwanted questions removed!")
    else:
        print("⚠️ WARNING - Some unwanted questions still present!")

    conn.close()

if __name__ == "__main__":
    verify()
