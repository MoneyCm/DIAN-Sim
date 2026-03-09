import os
import sqlite3
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Términos prohibidos (cualquiera de estos marcará el registro para eliminación)
BANNED_TERMS = [
    "Horizonte", "San Vicente", "LPN-2023-054", "Soluciones SAS", 
    "Comisión Nacional del Servicio Civil", "Villaflores", "Constructora Horizonte"
]

def nuclear_cleaning():
    print("--- ☢️ INICIANDO OPERACIÓN NUCLEAR DE LIMPIEZA ☢️ ---")

    # 1. Limpieza de NEON (Cloud)
    url = os.getenv("DATABASE_URL")
    if url:
        print("\n🧹 Limpiando NEON...")
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                # Buscar en casos
                cases = conn.execute(text("SELECT id, title, text FROM case_studies")).fetchall()
                for c_id, title, text_content in cases:
                    full_text = f"{title} {text_content}".lower()
                    if any(term.lower() in full_text for term in BANNED_TERMS):
                        print(f"   🗑️ Eliminando Caso en NEON: {title}")
                        conn.execute(text("DELETE FROM questions WHERE case_id = :id"), {"id": c_id})
                        conn.execute(text("DELETE FROM case_studies WHERE id = :id"), {"id": c_id})
                
                # Buscar en preguntas sueltas
                qs = conn.execute(text("SELECT question_id, stem, rationale FROM questions")).fetchall()
                for q_id, stem, rationale in qs:
                    full_text = f"{stem} {rationale}".lower()
                    if any(term.lower() in full_text for term in BANNED_TERMS):
                        print(f"   🗑️ Eliminando Pregunta en NEON: {q_id}")
                        conn.execute(text("DELETE FROM questions WHERE question_id = :id"), {"id": q_id})
                conn.commit()
        except Exception as e:
            print(f"   ❌ Error Neon: {e}")

    # 2. Limpieza de SQLite (Local)
    db_path = "dian_sim.db"
    if os.path.exists(db_path):
        print("\n🧹 Limpiando SQLITE...")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Casos
            cur.execute("SELECT id, title, text FROM case_studies")
            cases = cur.fetchall()
            for c_id, title, text_content in cases:
                full_text = f"{title} {text_content}".lower()
                if any(term.lower() in full_text for term in BANNED_TERMS):
                    print(f"   🗑️ Eliminando Caso en SQLITE: {title}")
                    cur.execute("DELETE FROM questions WHERE case_id = ?", (c_id,))
                    cur.execute("DELETE FROM case_studies WHERE id = ?", (c_id,))
            
            # Preguntas
            cur.execute("SELECT question_id, stem, rationale FROM questions")
            qs = cur.fetchall()
            for q_id, stem, rationale in qs:
                full_text = f"{stem} {rationale}".lower()
                if any(term.lower() in full_text for term in BANNED_TERMS):
                    print(f"   🗑️ Eliminando Pregunta en SQLITE: {q_id}")
                    cur.execute("DELETE FROM questions WHERE question_id = ?", (q_id,))
            
            conn.commit()
            
            # 3. VACUUM para limpiar el binario del archivo
            print("   🧨 Compactando archivo dian_sim.db (VACUUM)...")
            cur.execute("VACUUM")
            conn.close()
        except Exception as e:
            print(f"   ❌ Error SQLite: {e}")

    # 4. Limpieza de OPEC para todos los usuarios (Garantizar Gestor III DIAN)
    print("\n📦 Estandarizando OPEC para todos los usuarios...")
    # Usar el script que ya preparé anteriormente o integrar aquí
    # Se hará en un paso separado para mayor claridad.

    print("\n✅ LIMPIEZA COMPLETADA.")

if __name__ == "__main__":
    nuclear_cleaning()
