import sqlite3
import json

db_path = r'C:\Proyectos\DIAN-Sim\dian_sim.db'

def search_question(query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Search for questions containing the query in stem OR options
    # We use a more flexible search for large numbers or specific text
    cursor.execute("SELECT question_id, stem, options_json, correct_key, rationale FROM questions WHERE stem LIKE ? OR options_json LIKE ?", (f'%{query}%', f'%{query}%'))
    results = cursor.fetchall()
    
    if not results:
        print(f"No results found for '{query}'.")
        return
    
    print(f"Found {len(results)} matching questions:\n")
    for row in results:
        qid, stem, options, correct, rationale = row
        print(f"ID: {qid}")
        print(f"Stem: {stem}")
        print(f"Options: {options}")
        print(f"Correct Key: {correct}")
        print(f"Rationale: {rationale}")
        print("-" * 40)
    
    conn.close()

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "sanción"
    search_question(query)
