import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Agregar raíz al path para importar modelos si es necesario
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

MISTRAL_KEY = "r13W11htQUT3r4MgwNlBUHkk74SaMDLU"

try:
    with engine.connect() as conn:
        print(f"--- ⚙️ GUARDANDO MISTRAL_API_KEY EN NEON ---")
        conn.execute(text("""
            INSERT INTO configurations (key_name, value) 
            VALUES ('MISTRAL_API_KEY', :val) 
            ON CONFLICT (key_name) DO UPDATE SET value = :val
        """), {"val": MISTRAL_KEY})
        conn.commit()
        print("✅ MISTRAL_API_KEY guardada exitosamente en Neon.")
except Exception as e:
    print(f"❌ Error guardando la llave: {e}")
