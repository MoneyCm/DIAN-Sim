import sqlite3
import json

db_path = 'dian_sim.db'

def cleanup_format():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- CLEANUP: GOA FORMAT (3 OPTIONS FOR FUNCTIONAL) ---")
    
    cursor.execute("SELECT question_id, competency, topic, options_json FROM questions")
    rows = cursor.fetchall()
    
    ids_to_delete = []
    
    for r in rows:
        qid, comp, topic, opts_json = r
        try:
            options = json.loads(opts_json)
            num_opts = len(options)
            
            # Identify Behavioral
            is_behavioral = any(x in comp.lower() or x in topic.lower() for x in ['comportamental', 'conductual', 'integridad', 'valores', 'ética', 'etica'])
            
            if not is_behavioral:
                # Expect 3 options for Functional
                if num_opts != 3:
                     ids_to_delete.append(qid)
                     
        except Exception as e:
            print(f"Error parsing {qid}: {e}")

    print(f"Identified {len(ids_to_delete)} questions to delete.")
    
    if len(ids_to_delete) > 0:
        cursor.executemany("DELETE FROM questions WHERE question_id = ?", [(id,) for id in ids_to_delete])
        conn.commit()
        print(f"Successfully deleted {len(ids_to_delete)} rows.")
    
    cursor.execute("SELECT COUNT(*) FROM questions")
    final = cursor.fetchone()[0]
    print(f"Final DB Count: {final}")
    
    conn.close()

if __name__ == "__main__":
    cleanup_format()
