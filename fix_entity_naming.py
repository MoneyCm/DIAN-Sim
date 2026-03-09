import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
NEON_URL = os.getenv("DATABASE_URL")
engine = create_engine(NEON_URL)

try:
    with engine.connect() as conn:
        print("--- 🛠️ INICIANDO CORRECCIÓN MASIVA DE ENTIDAD ---")
        
        # Corregir en preguntas
        q_count = conn.execute(text("""
            UPDATE questions 
            SET stem = REPLACE(stem, 'Comisión Nacional del Servicio Civil', 'Dirección de Impuestos y Aduanas Nacionales (DIAN)')
            WHERE stem ILIKE '%Comisión Nacional del Servicio Civil%'
        """)).rowcount
        
        # Corregir en casos
        c_count = conn.execute(text("""
            UPDATE case_studies 
            SET text = REPLACE(text, 'Comisión Nacional del Servicio Civil', 'Dirección de Impuestos y Aduanas Nacionales (DIAN)'),
                title = REPLACE(title, 'Comisión Nacional del Servicio Civil', 'Dirección de Impuestos y Aduanas Nacionales (DIAN)')
            WHERE text ILIKE '%Comisión Nacional del Servicio Civil%' 
               OR title ILIKE '%Comisión Nacional del Servicio Civil%'
        """)).rowcount

        # Corregir siglas CNSC a DIAN si están en contexto de empleador
        q_count_2 = conn.execute(text("""
            UPDATE questions 
            SET stem = REPLACE(stem, 'Gestor III de Fiscalización de la CNSC', 'Gestor III de Fiscalización de la DIAN')
            WHERE stem ILIKE '%Gestor III de Fiscalización de la CNSC%'
        """)).rowcount
        
        conn.commit()
        print(f"Preguntas actualizadas: {q_count + q_count_2}")
        print(f"Casos actualizados: {c_count}")
        print("✅ Corrección masiva completada.")

except Exception as e:
    print(f"Error: {e}")
