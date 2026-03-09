import os
from sqlalchemy import create_engine, text

# URL proporcionada por el usuario
DATABASE_URL = "postgresql://neondb_owner:npg_2rViwYLTN3bM@ep-empty-paper-ai2z00om-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"

def verify_neon_cloud():
    print(f"--- 🛰️ VERIFICANDO NEON CLOUD (URL USUARIO) ---")
    try:
        # Quitamos channel_binding si da problemas, Neon suele preferir sslmode=require
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("✅ Conexión exitosa a Neon.")
            
            # Contar registros
            cases_count = conn.execute(text("SELECT count(*) FROM case_studies")).scalar()
            questions_count = conn.execute(text("SELECT count(*) FROM questions")).scalar()
            print(f"📊 Estadísticas: {cases_count} casos, {questions_count} preguntas.")
            
            # Buscar Horizonte
            res = conn.execute(text("SELECT id, title FROM case_studies WHERE title ILIKE '%Horizonte%' OR text ILIKE '%Horizonte%'")).fetchall()
            if res:
                print(f"⚠️ ¡ALERTA! Se encontraron {len(res)} casos de Horizonte en NEON.")
                for r in res:
                    print(f"   - {r[1]} (ID: {r[0]})")
            else:
                print("✅ No hay rastro de 'Horizonte' en NEON.")
                
            # Verificar OPEC del Admin
            user_opec = conn.execute(text("SELECT opec_number, requirements FROM user_opec LIMIT 5")).fetchall()
            print("\n📋 Muestra de OPEC/Requisitos en DB:")
            for row in user_opec:
                print(f"   - OPEC: {row[0]} | Requisitos: {row[1][:100]}...")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    verify_neon_cloud()
