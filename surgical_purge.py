import os
import sqlite3
import sys

# Ruta reportada por el usuario en Streamlit Cloud
DB_PATH = "/mount/src/dian-sim/dian_sim.db"

def final_surgical_purge():
    target = DB_PATH if os.path.exists(DB_PATH) else "dian_sim.db"
    print(f"--- 🩺 CIRUGÍA DE LIMPIEZA EN {target} ---")
    
    if not os.path.exists(target):
        print("❌ Error: Base de datos no encontrada.")
        return

    try:
        conn = sqlite3.connect(target)
        cur = conn.cursor()
        
        # Términos prohibidos específicos
        banned = ["Horizonte", "San Vicente", "LPN-2023-054", "Soluciones SAS", "CNSC"]
        
        for term in banned:
            print(f"🔍 Buscando '{term}'...")
            
            # Borrar preguntas
            cur.execute("DELETE FROM questions WHERE stem LIKE ?", (f'%{term}%',))
            qs_deleted = cur.rowcount
            
            # Borrar casos (y sus preguntas asociadas)
            cur.execute("SELECT id FROM case_studies WHERE title LIKE ? OR text LIKE ?", (f'%{term}%', f'%{term}%'))
            case_ids = [r[0] for r in cur.fetchall()]
            
            for cid in case_ids:
                cur.execute("DELETE FROM questions WHERE case_id = ?", (cid,))
                cur.execute("DELETE FROM case_studies WHERE id = ?", (cid,))
            
            cases_deleted = len(case_ids)
            print(f"   🗑️ Eliminados: {qs_deleted} preguntas y {cases_deleted} casos con '{term}'.")

        # Compactar archivo
        print("🧨 Ejecutando VACUUM para eliminar rastros físicos...")
        cur.execute("VACUUM")
        conn.commit()
        conn.close()
        print("✅ LIMPIEZA QUIRÚRGICA FINALIZADA.")
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    final_surgical_purge()
