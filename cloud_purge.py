import sqlite3
import os

# Ruta reportada por el usuario en el diagnóstico
DB_PATH = "/mount/src/dian-sim/dian_sim.db"

# Términos prohibidos para la purga
BANNED_TERMS = [
    "Horizonte", "San Vicente", "LPN-2023-054", "Soluciones SAS", 
    "Comisión Nacional del Servicio Civil", "Villaflores", "CNSC", "irregu", "contrataci"
]

def cloud_sqlite_purge():
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró el archivo en {DB_PATH}")
        # Intentar ruta relativa por si acaso
        DB_PATH_ALT = "dian_sim.db"
        if os.path.exists(DB_PATH_ALT):
            print(f"🔍 Usando ruta alternativa: {DB_PATH_ALT}")
            target_db = DB_PATH_ALT
        else:
            print("❌ No se encontró dian_sim.db en ninguna ubicación.")
            return
    else:
        target_db = DB_PATH

    print(f"🧹 Iniciando purga en: {target_db}")
    try:
        conn = sqlite3.connect(target_db)
        cur = conn.cursor()
        
        # 1. Eliminar casos que contengan términos prohibidos
        count_cases = 0
        cur.execute("SELECT id, title, text FROM case_studies")
        for row in cur.fetchall():
            case_id, title, text_val = row
            content = f"{title} {text_val}".lower()
            if any(term.lower() in content for term in BANNED_TERMS):
                cur.execute("DELETE FROM questions WHERE case_id = ?", (case_id,))
                cur.execute("DELETE FROM case_studies WHERE id = ?", (case_id,))
                count_cases += 1
        
        # 2. Eliminar preguntas sueltas que contengan términos prohibidos
        cur.execute("SELECT question_id, stem FROM questions")
        count_qs = 0
        for row in cur.fetchall():
            q_id, stem = row
            if any(term.lower() in (stem or "").lower() for term in BANNED_TERMS):
                cur.execute("DELETE FROM questions WHERE question_id = ?", (q_id,))
                count_qs += 1
                
        # 3. Compactar para borrar rastros binarios
        cur.execute("VACUUM")
        conn.commit()
        conn.close()
        
        print(f"✅ Purga completada. Casos eliminados: {count_cases}, Preguntas eliminadas: {count_qs}")
        print("✨ VACUUM ejecutado exitosamente.")
        
    except Exception as e:
        print(f"❌ Error durante la purga: {e}")

if __name__ == "__main__":
    cloud_sqlite_purge()
