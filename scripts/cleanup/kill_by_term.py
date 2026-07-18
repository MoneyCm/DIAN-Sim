import sqlite3

DB_PATH = "dian_sim.db"

def find_and_kill(term):
    print(f"\n--- 🎯 BUSCANDO Y ELIMINANDO: '{term}' ---")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    
    deleted_total = 0
    
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cur.fetchall()]
        
        # Identificar columna ID
        id_col = cols[0] # Usualmente la primera es ID
        for c in cols:
            if "id" in c.lower():
                id_col = c
                break
        
        for col in cols:
            try:
                # Usar LIKE con comodines
                cur.execute(f"SELECT {id_col}, {col} FROM {table} WHERE {col} LIKE ?", (f"%{term}%",))
                rows = cur.fetchall()
                for r in rows:
                    target_id = r[0]
                    content_preview = str(r[1])[:50]
                    print(f"📍 Hallado en {table}.{col} | ID: {target_id} | Preview: {content_preview}...")
                    
                    # Borrar por ID para ser precisos
                    cur.execute(f"DELETE FROM {table} WHERE {id_col} = ?", (target_id,))
                    deleted_total += cur.rowcount
            except Exception as e:
                pass
                
    conn.commit()
    conn.close()
    print(f"✅ Total eliminados para '{term}': {deleted_total}")

# Términos específicos basados en el reporte del usuario
find_and_kill("Horizonte")
find_and_kill("LPN-2023-054")
find_and_kill("San Vicente")
find_and_kill("Constructora Soluciones") # Por si acaso
