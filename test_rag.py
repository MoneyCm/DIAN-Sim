
import os, sys
# Setup paths
PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.normativa import NormativaManager
from db.session import SessionLocal
from db.models import NormativaChunk

def test_rag():
    print("🚀 Iniciando prueba de RAG v48.0...")
    manager = NormativaManager()
    
    # 1. Verificar si hay datos
    db = SessionLocal()
    count = db.query(NormativaChunk).count()
    print(f"📊 Chunks actuales en BD: {count}")
    
    if count == 0:
        print("📥 El banco está vacío. Iniciando indexación manual...")
        indexed = manager.index_all(lambda p, m: print(f"   [{p}%] {m}"))
        print(f"✅ Se indexaron {indexed} fragmentos.")
    else:
        print("✨ Saltando indexación (ya hay datos).")

    # 2. Probar búsqueda
    test_query = "Régimen Simple de Tributación"
    print(f"\n🔍 Buscando: '{test_query}'...")
    results = manager.search_in_laws(test_query, limit=3)
    
    if results:
        for i, res in enumerate(results):
            print(f"\n--- Resultado {i+1} (Score: {res['score']}) ---")
            print(f"Fuente: {res['source']} (Pág. {res['page']})")
            print(f"Contenido: {res['snippet'][:200]}...")
    else:
        print("❌ No se encontraron resultados para la búsqueda.")
    
    db.close()

if __name__ == "__main__":
    test_rag()
