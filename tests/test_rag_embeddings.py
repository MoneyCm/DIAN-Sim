import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.normativa import NormativaManager
import json

def test_cosine_similarity():
    # Simular cálculo matemático en modulo de normativa
    from core.normativa import cosine_similarity
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0
    assert cosine_similarity(v1, v3) == 0.0
    print("Prueba de similitud de coseno exitosa.")

def test_search_fallback():
    manager = NormativaManager()
    # Probar que la busqueda no lance excepciones aunque no haya embeddings o llaves
    results = manager.search_in_laws("impuesto de renta")
    assert isinstance(results, list), "El resultado de la busqueda debe ser una lista"
    print("Prueba de fallback exitosa.")

if __name__ == "__main__":
    test_cosine_similarity()
    test_search_fallback()
