import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- ☁️ VERIFICACIÓN EN TIEMPO REAL RECUPERADA DE NEON ---")
        # Contar preguntas generadas hoy para OPEC 236769
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM questions 
            WHERE topic LIKE '%236769%' AND source_refs LIKE '%Mistral%'
        """))
        count = result.scalar()
        print(f"Preguntas encontradas en NEON (Nube): {count}")
        
        if count > 0:
            print("\nÚltimo registro insertado:")
            sample = conn.execute(text("""
                SELECT topic, LEFT(stem, 80) as stem_preview, difficulty 
                FROM questions 
                WHERE topic LIKE '%236769%' 
                ORDER BY created_at DESC LIMIT 1
            """)).fetchone()
            print(f"- Tema: {sample.topic} | Dificultad: {sample.difficulty} | Preview: {sample.stem_preview}...")

except Exception as e:
    print(f"Error consultando Neon: {e}")
