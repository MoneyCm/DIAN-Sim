import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def inspect_db(db_url, db_name):
    print(f"\n🕵️ Inspeccionando {db_name}...")
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # 1. Total de preguntas y preguntas únicas
            res = conn.execute(text("SELECT COUNT(*) FROM questions")).scalar()
            res_uniq = conn.execute(text("SELECT COUNT(DISTINCT question_id) FROM questions")).scalar()
            print(f"   - Total Preguntas: {res}")
            print(f"   - Question IDs Únicos: {res_uniq}")
            
            # 2. ¿Hay stems duplicados?
            res_stems = conn.execute(text("SELECT COUNT(DISTINCT stem) FROM questions")).scalar()
            print(f"   - Stems Únicos: {res_stems}")
            
            # 3. Mostrar algunas preguntas
            samples = conn.execute(text("SELECT question_id, topic, LEFT(stem, 60) FROM questions LIMIT 5") if "postgres" in db_url else text("SELECT question_id, topic, substr(stem, 1, 60) FROM questions LIMIT 5")).fetchall()
            print("   - Muestras:")
            for s in samples:
                print(f"     * ID: {s[0]} | Topic: {s[1]} | Stem: {s[2]}...")
                
            # 4. Agrupamiento de stems duplicados para ver si hay un problema
            dups = conn.execute(text("""
                SELECT stem, COUNT(*) 
                FROM questions 
                GROUP BY stem 
                HAVING COUNT(*) > 1 
                LIMIT 5
            """)).fetchall()
            if dups:
                print("   - ⚠️ Stems Duplicados Detectados:")
                for d in dups:
                    print(f"     * count: {d[1]} | stem: {d[0][:80]}...")
            else:
                print("   - ✅ No hay stems duplicados en la tabla.")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    # SQLite
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    inspect_db(f"sqlite:///{os.path.join(PROJECT_ROOT, 'dian_sim.db')}", "SQLite Local")
    
    # Neon
    neon_url = os.getenv("DATABASE_URL")
    if neon_url:
        if neon_url.startswith("postgres://") or neon_url.startswith("postgresql://"):
            neon_url = neon_url.replace("postgres://", "postgresql+psycopg2://", 1)
            neon_url = neon_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            if "channel_binding=" in neon_url:
                import re
                neon_url = re.sub(r'[&?]channel_binding=[^&]*', '', neon_url)
        inspect_db(neon_url, "PostgreSQL Cloud")

if __name__ == "__main__":
    main()
