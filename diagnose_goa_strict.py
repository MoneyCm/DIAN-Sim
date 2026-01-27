import sqlite3

db_path = 'dian_sim.db'

def diagnose_goa_strict():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- DIAGNOSTIC: STRICT GOA COMPLIANCE ---")
    
    # 1. Total Current
    cursor.execute("SELECT COUNT(*) FROM questions")
    total = cursor.fetchone()[0]
    print(f"Total Current Questions: {total}")

    # 2. Strict GOA (Has 'SITUACIÓN')
    cursor.execute("SELECT COUNT(*) FROM questions WHERE stem LIKE '%SITUACIÓN%'")
    goa_strict = cursor.fetchone()[0]
    print(f"Strict GOA (Situational): {goa_strict}")

    # 3. Non-GOA (To Delete if strict)
    cursor.execute("SELECT COUNT(*) FROM questions WHERE stem NOT LIKE '%SITUACIÓN%'")
    non_goa = cursor.fetchone()[0]
    print(f"Non-GOA (Direct/Concept): {non_goa}")
    
    # Sample Non-GOA
    if non_goa > 0:
        print("\n=== SAMPLE NON-GOA QUESTIONS ===")
        cursor.execute("SELECT topic, stem FROM questions WHERE stem NOT LIKE '%SITUACIÓN%' LIMIT 5")
        rows = cursor.fetchall()
        for r in rows:
            print(f"Topic: {r[0]} | Stem: {r[1][:50]}...")

    conn.close()

if __name__ == "__main__":
    diagnose_goa_strict()
