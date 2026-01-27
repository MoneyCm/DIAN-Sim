import sqlite3
import bcrypt
import json
from datetime import datetime

db_path = 'dian_sim.db'

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def repair_users():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- REPAIRING USERS & PASSWORDS ---")

    # 1. Admin User (Password: 1234)
    admin_pass = hash_password("1234")
    
    # Check if admin exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_row = cursor.fetchone()
    
    if admin_row:
        print("Updating admin password...")
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (admin_pass, admin_row[0]))
    else:
        print("Creating admin user...")
        cursor.execute("""
            INSERT INTO users (username, role, created_at, password_hash)
            VALUES ('admin', 'admin', ?, ?)
        """, (datetime.now(), admin_pass))
    
    print("Admin user secure (Pass: 1234)")

    # 2. Cesar User (OPEC 236844) - Restoring for Dynamic Filter
    # Check if cesar exists
    cursor.execute("SELECT id FROM users WHERE username = 'cesar'")
    cesar_row = cursor.fetchone()
    
    if cesar_row:
        user_id = cesar_row[0]
        print(f"User 'cesar' exists (ID: {user_id}).")
    else:
        print("Re-creating 'cesar' user...")
        # Note: We can use a dummy password or the same hash for testing
        cesar_pass = hash_password("1234") 
        cursor.execute("""
            INSERT INTO users (username, role, created_at, password_hash)
            VALUES ('cesar', 'user', ?, ?)
        """, (datetime.now(), cesar_pass))
        user_id = cursor.lastrowid
        print(f"Created 'cesar' (ID: {user_id})")

    # 3. Configure Cesar's OPEC (236844)
    opec_data = {
        "opec_number": "236844",
        "job_title": "GESTOR II",
        "level": "PROFESIONAL",
        "purpose": "Desarrollar acciones inherentes al proceso de cumplimiento de obligaciones tributarias (Recaudación y Cobranzas).",
        "functions": [
            "Adelantar las diligencias de los procesos que le sean asignados relacionados con la administración de cartera.",
            "Aplicar mecanismos de control en el cumplimiento de las obligaciones tributarias.",
            "Corregir los datos inconsistentes de las declaraciones.",
            "Gestionar sistemas de información de recaudación.",
            "Depurar información del estado de cuenta del contribuyente.",
            "Representar a la UAE DIAN en procesos especiales.",
            "Responder por la incorporación de información.",
            "Tramitar solicitudes de devoluciones y/o compensaciones."
        ],
        "requirements": "Título Profesional. 12 meses de experiencia."
    }

    # Clear old OPEC
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
        json.dumps(opec_data["functions"]),
        opec_data["requirements"], 
        datetime.now()
    ))
    
    print(f"User 'cesar' restored with OPEC {opec_data['opec_number']}.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    repair_users()
