import sqlite3
import os

db_path = r'C:\Proyectos\DIAN-Sim\dian_sim.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    for table_tuple in tables:
        table_name = table_tuple[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Table '{table_name}' has {count} rows.")
    
    conn.close()
