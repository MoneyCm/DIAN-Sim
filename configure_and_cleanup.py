import sqlite3
import json
from datetime import datetime

db_path = 'dian_sim.db'

def configure_user():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- CONFIGURING USER 'CESAR' FOR OPEC 236844 ---")

    # 1. Ensure User Exists
    cursor.execute("SELECT id FROM users WHERE username = 'cesar'")
    user = cursor.fetchone()
    
    if not user:
        print("User 'cesar' not found. Creating...")
        cursor.execute("""
            INSERT INTO users (username, role, created_at, password_hash)
            VALUES ('cesar', 'user', ?, 'dummy_hash')
        """, (datetime.now(),))
        user_id = cursor.lastrowid
    else:
        user_id = user[0]
        print(f"User 'cesar' found (ID: {user_id}).")

    # 2. Configure UserOPEC
    opec_data = {
        "opec_number": "236844",
        "job_title": "GESTOR II",
        "level": "PROFESIONAL",
        "purpose": "Desarrollar acciones inherentes al proceso de cumplimiento de obligaciones tributarias (Recaudación y Cobranzas).",
        "functions": [
            "Adelantar las diligencias de los procesos que le sean asignados relacionados con la administración de cartera.",
            "Aplicar mecanismos de control en el cumplimiento de las obligaciones tributarias (autorretenedores, grandes contribuyentes, IVA).",
            "Corregir los datos inconsistentes de las declaraciones, recibos de pago y reproceso de saldos.",
            "Gestionar la creación, modificación y operación de sistemas de información de recaudación y cartera.",
            "Realizar las actividades tendientes a depurar la información del estado de cuenta del contribuyente.",
            "Representar a la UAE DIAN en los procesos especiales y/o concursales.",
            "Responder por la incorporación y calidad de la información sobre obligaciones a normalizar.",
            "Tramitar las solicitudes de devoluciones y/o compensaciones."
        ],
        "requirements": "Título Profesional en Administración, Contaduría, Derecho, Economía o Ingenierías afines. 12 meses de experiencia."
    }

    # Deactivate old OPEC configs
    cursor.execute("UPDATE user_opec SET is_active = 0 WHERE user_id = ?", (user_id,))
    
    # Insert New OPEC
    cursor.execute("""
        INSERT INTO user_opec (user_id, opec_number, job_title, level, purpose, functions, requirements, is_active, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        user_id, 
        opec_data["opec_number"], 
        opec_data["job_title"], 
        opec_data["level"], 
        opec_data["purpose"], 
        json.dumps(opec_data["functions"]), # JSON
        opec_data["requirements"], 
        datetime.now()
    ))
    
    print(f"User 'cesar' configured with OPEC {opec_data['opec_number']} active.")
    conn.commit()
    conn.close()

def cleanup_customs():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    keywords = [
        'Aduan', 'Import', 'Export', 'Tránsito', 'Transito', 
        'Cabotaje', 'Zona Franca', 'Cambiari', 'Transporte', 
        'Arancel'
    ]
    query_or = " OR ".join([f"topic LIKE '%{kw}%' OR competency LIKE '%{kw}%'" for kw in keywords])
    
    print("\n--- CLEANING UP NON-OPEC TOPICS (CUSTOMS/FOREIGN TRADE) ---")
    cursor.execute(f"DELETE FROM questions WHERE {query_or}")
    deleted = cursor.rowcount
    conn.commit()
    print(f"Deleted {deleted} questions related to Customs/Foreign Trade.")
    
    cursor.execute("SELECT COUNT(*) FROM questions")
    final_count = cursor.fetchone()[0]
    print(f"Final Database Count: {final_count}")
    
    conn.close()

if __name__ == "__main__":
    configure_user()
    cleanup_customs()
