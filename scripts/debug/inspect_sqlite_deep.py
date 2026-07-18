import sqlite3
import os

DB_PATH = "dian_sim.db"

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("--- 🏛️ ESQUEMA DE TABLAS ---")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    for t in tables:
        print(f"Tabla: {t[0]}")
    
    print("\n--- 🔍 BÚSQUEDA EXHAUSTIVA DE 'HORIZONTE' EN TODAS LAS TABLAS ---")
    for t in tables:
        table_name = t[0]
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = [c[1] for c in cur.fetchall()]
        
        for col in cols:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col} LIKE '%Horizonte%'")
                count = cur.fetchone()[0]
                if count > 0:
                    print(f"¡ENCONTRADO! Tabla: {table_name} | Columna: {col} | Conteo: {count}")
                    # Mostrar una muestra
                    cur.execute(f"SELECT {col} FROM {table_name} WHERE {col} LIKE '%Horizonte%' LIMIT 1")
                    print(f"Muestra: {cur.fetchone()[0][:100]}...")
            except:
                pass # Probablemente no es una columna de texto
                
    conn.close()
except Exception as e:
    print(f"Error: {e}")
