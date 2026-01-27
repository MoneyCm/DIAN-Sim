import sqlite3

db_path = 'dian_sim.db'

def diagnose_profound():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    keywords = [
        'Aduan', 'Import', 'Export', 'Tránsito', 'Transito', 
        'Cabotaje', 'Zona Franca', 'Cambiari', 'Transporte', 
        'Arancel'
    ]
    
    print("--- DIAGNOSTIC: ADUANAS/CAMBIARIA vs TRIBUTARIA ---")
    
    total_customs = 0
    for kw in keywords:
        cursor.execute(f"SELECT COUNT(*) FROM questions WHERE topic LIKE '%{kw}%' OR competency LIKE '%{kw}%'")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"Keyword '{kw}': {count} matches")
            total_customs += count

    # Combined query for unique count to delete
    query_or = " OR ".join([f"topic LIKE '%{kw}%' OR competency LIKE '%{kw}%'" for kw in keywords])
    cursor.execute(f"SELECT COUNT(*) FROM questions WHERE {query_or}")
    unique_to_delete = cursor.fetchone()[0]
    
    print(f"\nTotal Unique Questions to Delete (Non-OPEC 236844): {unique_to_delete}")
    
    # Verify what remains
    cursor.execute("SELECT COUNT(*) FROM questions")
    total_now = cursor.fetchone()[0]
    print(f"Current Total: {total_now}")
    print(f"Estimated Post-Cleanup: {total_now - unique_to_delete}")

    conn.close()

if __name__ == "__main__":
    diagnose_profound()
