import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")

if not NEON_URL or "neon.tech" not in NEON_URL:
    print("❌ ERROR: No se encontró una URL de Neon válida en el archivo .env")
    exit(1)

print(f"🔍 Verificando datos en Neon ({NEON_URL.split('@')[1].split('/')[0]})...")

engine = create_engine(NEON_URL)
Session = sessionmaker(bind=engine)
session = Session()

tables = ["users", "case_studies", "questions"]

try:
    for table in tables:
        result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"📊 Tabla '{table}': {count} registros.")
    
    print("\n✅ Verificación completada.")
except Exception as e:
    print(f"❌ Error al consultar Neon: {e}")
finally:
    session.close()
