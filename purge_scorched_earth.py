import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

terms_to_purge = [
    '%Comisión Nacional del Servicio Civil%',
    '%CNSC%',
    '%Ley 80%',
    '%Horizonte%',
    '%San Vicente%',
    '%LPN-2023-054%',
    '%Alcaldía%',
    '%Movimiento de tierras%',
    '%RUP%'
]

try:
    with engine.connect() as conn:
        print("--- 🔥 OPERACIÓN TIERRA QUEMADA: ELIMINANDO RASTROS DE CNSC ---")
        
        total_q_deleted = 0
        total_c_deleted = 0
        
        for term in terms_to_purge:
            # Eliminar preguntas que contengan el término en stem o rationale
            q_res = conn.execute(text("""
                DELETE FROM questions 
                WHERE stem ILIKE :term OR rationale ILIKE :term
            """), {"term": term})
            total_q_deleted += q_res.rowcount
            
            # Eliminar casos que contengan el término en text o title
            c_res = conn.execute(text("""
                DELETE FROM case_studies 
                WHERE text ILIKE :term OR title ILIKE :term
            """), {"term": term})
            total_c_deleted += c_res.rowcount
            
        conn.commit()
        print(f"Total de preguntas eliminadas: {total_q_deleted}")
        print(f"Total de casos eliminados: {total_c_deleted}")
        
        # Verificar si queda algo
        verify = conn.execute(text("SELECT COUNT(*) FROM case_studies WHERE title ILIKE '%Horizonte%'"))
        print(f"Casos restantes con 'Horizonte': {verify.scalar()}")
        
except Exception as e:
    print(f"Error: {e}")
