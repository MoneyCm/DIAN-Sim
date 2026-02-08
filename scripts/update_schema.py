"""
Script para actualizar el esquema de la base de datos local
Agrega la columna case_id a la tabla questions
"""
import sqlite3
import os

# Ruta a la base de datos
db_path = os.path.join(os.path.dirname(__file__), "..", "dian_sim.db")

print(f"Actualizando esquema de: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar si la columna ya existe
cursor.execute("PRAGMA table_info(questions)")
columns = [row[1] for row in cursor.fetchall()]

if 'case_id' not in columns:
    print("Agregando columna case_id a la tabla questions...")
    try:
        cursor.execute("ALTER TABLE questions ADD COLUMN case_id VARCHAR(36)")
        conn.commit()
        print("✅ Columna case_id agregada exitosamente")
    except Exception as e:
        print(f"❌ Error al agregar columna: {e}")
else:
    print("✅ La columna case_id ya existe")

# Verificar que la tabla case_studies existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='case_studies'")
if cursor.fetchone():
    print("✅ La tabla case_studies ya existe")
else:
    print("Creando tabla case_studies...")
    cursor.execute("""
        CREATE TABLE case_studies (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR,
            text TEXT NOT NULL,
            difficulty INTEGER DEFAULT 2,
            topic VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("✅ Tabla case_studies creada exitosamente")

conn.close()
print("\n✅ Esquema actualizado correctamente")
