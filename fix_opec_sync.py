from sqlalchemy import create_engine, text
import os
import sys
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def fix_user_opec_mismatch():
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL no está configurada; no se realizará ninguna modificación.")
    if "sqlite" in DATABASE_URL.lower():
        raise SystemExit("Este script está destinado a PostgreSQL/Neon, no a SQLite local.")
    print("ðŸš€ Ajustando Mismatch de OPEC en Neon...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # 1. Corregir el nÃºmero de OPEC para el usuario Cesar (ID 2)
            # El usuario reportÃ³ 236769 en los requisitos pero el diagnÃ³stico dice 236739
            conn.execute(text("""
                UPDATE user_opec 
                SET opec_number = '236769' 
                WHERE user_id = 2 AND opec_number = '236739'
            """))
            
            # 2. Asegurar que los Requisitos de NBC sean los correctos
            req_text = "TÃ­tulo de PROFESIONAL en NBC: ADMINISTRACION ,O, NBC: CIENCIA POLITICA, RELACIONES INTERNACIONALES ,O, NBC: CONTADURIA PUBLICA ,O, NBC: DERECHO Y AFINES ,O, NBC: ECONOMIA ,O, NBC: INGENIERIA ADMINISTRATIVA Y AFINES ,O, NBC: INGENIERIA DE SISTEMAS, TELEMATICA Y AFINES ,O, NBC: INGENIERIA INDUSTRIAL Y AFINES ,O, NBC: INGENIERIA QUIMICA Y AFINES ,O, NBC: MATEMATICAS, ESTADISTICA Y AFINES."
            conn.execute(text("""
                UPDATE user_opec 
                SET requirements = :req
                WHERE opec_number = '236769'
            """), {"req": req_text})
            
            conn.commit()
            print("âœ… OPEC y Requisitos sincronizados en Neon.")
            
    except Exception as e:
        print(f"âŒ Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    fix_user_opec_mismatch()


