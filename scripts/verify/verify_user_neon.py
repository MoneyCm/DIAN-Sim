import os
from sqlalchemy import create_engine, text

# URL proporcionada por el usuario
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL no está configurada.")

def verify_neon_cloud():
    print(f"--- ðŸ›°ï¸ VERIFICANDO NEON CLOUD (URL USUARIO) ---")
    try:
        # Quitamos channel_binding si da problemas, Neon suele preferir sslmode=require
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("âœ… ConexiÃ³n exitosa a Neon.")
            
            # Muestra de casos
            cases = conn.execute(text("SELECT title, LEFT(text, 200) FROM case_studies LIMIT 1")).fetchall()
            print("\nðŸ“‹ Muestra de Casos:")
            for c in cases:
                print(f"   - TÃ­tulo: {c[0]}")
                print(f"   - Texto (inicio): {c[1]}...")
                text_full = conn.execute(text("SELECT text FROM case_studies WHERE title = :t"), {"t": c[0]}).scalar()
                print(f"   - Â¿Contiene 'DIAN'? {'SÃ' if 'DIAN' in text_full.upper() else 'NO'}")
                print(f"   - Â¿Contiene tÃ©rminos prohibidos? {any(t in text_full.lower() for t in ['horizonte', 'cnsc'])}")
            
            # Buscar Horizonte
            res = conn.execute(text("SELECT id, title FROM case_studies WHERE title ILIKE '%Horizonte%' OR text ILIKE '%Horizonte%'")).fetchall()
            if res:
                print(f"âš ï¸ Â¡ALERTA! Se encontraron {len(res)} casos de Horizonte en NEON.")
                for r in res:
                    print(f"   - {r[1]} (ID: {r[0]})")
            else:
                print("âœ… No hay rastro de 'Horizonte' en NEON.")
                
            # Verificar OPEC del Admin
            user_opec = conn.execute(text("SELECT opec_number, requirements FROM user_opec LIMIT 5")).fetchall()
            print("\nðŸ“‹ Muestra de OPEC/Requisitos en DB:")
            for row in user_opec:
                print(f"   - OPEC: {row[0]} | Requisitos: {row[1][:100]}...")
            
    except Exception as e:
        print(f"âŒ Error de conexiÃ³n: {e}")

if __name__ == "__main__":
    verify_neon_cloud()

