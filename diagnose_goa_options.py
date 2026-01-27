import sqlite3
import json

db_path = 'dian_sim.db'

def diagnose_options():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- DIAGNOSTIC: GOA FORMAT (OPTIONS COUNT) ---")
    
    cursor.execute("SELECT question_id, competency, topic, options_json FROM questions")
    rows = cursor.fetchall()
    
    functional_3_opts = 0
    functional_4_opts = 0
    behavioral_3_opts = 0
    behavioral_4_opts = 0
    
    # Heuristic for Behavioral: 
    # Usually competencies like 'Integridad', 'Trabajo en equipo', 'Orientación a resultados'
    # But current DB seems to be filtered for 'Gestor II'. 
    # Let's see if 'Gestor II' topic implies Functional purely.
    
    mismatches = []
    
    for r in rows:
        qid, comp, topic, opts_json = r
        try:
            options = json.loads(opts_json)
            num_opts = len(options)
            
            # Classification Heuristic
            # We assume most 'Gestor II' questions are FUNCTIONAL unless explicitly Behavioral topics
            is_behavioral = any(x in comp.lower() or x in topic.lower() for x in ['comportamentals', 'conductual', 'integridad', 'valores', 'ética', 'etica'])
            
            if is_behavioral:
                if num_opts == 4:
                    behavioral_4_opts += 1
                else:
                    behavioral_3_opts += 1
                    mismatches.append(f"[BEHAVIORAL MISMATCH] ID: {qid} | Opts: {num_opts} | Comp: {comp}")
            else:
                # Functional
                if num_opts == 3:
                    functional_3_opts += 1
                else:
                    functional_4_opts += 1
                    mismatches.append(f"[FUNCTIONAL MISMATCH] ID: {qid} | Opts: {num_opts} | Comp: {comp} | Topic: {topic}")
                    
        except Exception as e:
            print(f"Error parsing JSON for {qid}: {e}")

    print(f"\nFunctional (Expected 3 options):")
    print(f"  - Matches (3 opts): {functional_3_opts}")
    print(f"  - Mismatches (NOT 3 opts): {functional_4_opts}")
    
    print(f"\nBehavioral (Expected 4 options/Likert):")
    print(f"  - Matches (4 opts): {behavioral_4_opts}")
    print(f"  - Mismatches (NOT 4 opts): {behavioral_3_opts}")
    
    if len(mismatches) > 0:
        print("\n--- SAMPLE MISMATCHES (To be Deleted?) ---")
        for m in mismatches[:10]:
            print(m)
            
    conn.close()

if __name__ == "__main__":
    diagnose_options()
