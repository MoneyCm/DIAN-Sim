import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- ⚙️ CONTENIDO DE LA TABLA CONFIGURATIONS ---")
        result = conn.execute(text("SELECT key_name, value FROM configurations"))
        rows = result.fetchall()
        if not rows:
            print("La tabla 'configurations' está vacía o no existe.")
        for row in rows:
            # Mostrar solo los primeros 4 caracteres de la clave por seguridad
            masked_val = row.value[:4] + "..." if row.value else "None"
            print(f"Key: {row.key_name} | Value (masked): {masked_val}")
except Exception as e:
    print(f"Error: {e}")
