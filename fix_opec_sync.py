from sqlalchemy import create_engine, text
import sys

# URL de Neon del usuario
DATABASE_URL = "postgresql://neondb_owner:npg_2rViwYLTN3bM@ep-empty-paper-ai2z00om-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"

def fix_user_opec_mismatch():
    print("🚀 Ajustando Mismatch de OPEC en Neon...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # 1. Corregir el número de OPEC para el usuario Cesar (ID 2)
            # El usuario reportó 236769 en los requisitos pero el diagnóstico dice 236739
            conn.execute(text("""
                UPDATE user_opec 
                SET opec_number = '236769' 
                WHERE user_id = 2 AND opec_number = '236739'
            """))
            
            # 2. Asegurar que los Requisitos de NBC sean los correctos
            req_text = "Título de PROFESIONAL en NBC: ADMINISTRACION ,O, NBC: CIENCIA POLITICA, RELACIONES INTERNACIONALES ,O, NBC: CONTADURIA PUBLICA ,O, NBC: DERECHO Y AFINES ,O, NBC: ECONOMIA ,O, NBC: INGENIERIA ADMINISTRATIVA Y AFINES ,O, NBC: INGENIERIA DE SISTEMAS, TELEMATICA Y AFINES ,O, NBC: INGENIERIA INDUSTRIAL Y AFINES ,O, NBC: INGENIERIA QUIMICA Y AFINES ,O, NBC: MATEMATICAS, ESTADISTICA Y AFINES."
            conn.execute(text("""
                UPDATE user_opec 
                SET requirements = :req
                WHERE opec_number = '236769'
            """), {"req": req_text})
            
            conn.commit()
            print("✅ OPEC y Requisitos sincronizados en Neon.")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    fix_user_opec_mismatch()
