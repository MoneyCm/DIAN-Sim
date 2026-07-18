import sqlite3

DB_PATH = "dian_sim.db"
TARGET_ID = "8ad0c3bb-ee3f-4e5c-969e-dc6cab6351e4"

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cur.fetchall()]
        
        for col in cols:
            try:
                cur.execute(f"SELECT * FROM {table} WHERE {col} = ?", (TARGET_ID,))
                row = cur.fetchone()
                if row:
                    print(f"✅ ENCONTRADO en Tabla: {table} | Columna: {col}")
                    print(f"Contenido: {row}")
                    # Eliminar inmediatamente
                    cur.execute(f"DELETE FROM {table} WHERE {col} = ?", (TARGET_ID,))
                    print(f"🗑️ Registro eliminado de {table}.")
            except:
                pass
                
    conn.commit()
    conn.close()
    print("✅ Búsqueda y eliminación por ID completada.")
except Exception as e:
    print(f"Error: {e}")
