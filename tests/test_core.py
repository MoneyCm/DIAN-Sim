import pytest
from core.dedupe import normalize_text, compute_hash, find_duplicates
from core.adaptive import calculate_mastery_update

def test_normalization():
    raw = "  ¡Hóla!  Mundo. "
    expected = "hola mundo"
    assert normalize_text(raw) == expected

def test_hashing_consistency():
    t1 = "Texto de Prueba"
    t2 = "texto de prueba..."
    assert compute_hash(t1) == compute_hash(t2)

def test_deduplication_detection():
    existing = ["pregunta sobre impuestos", "definicion de iva"]
    new_q = "Pregunta SOBRE Impuestos"
    matches = find_duplicates(new_q, existing)
    assert len(matches) > 0
    assert matches[0][0] == "pregunta sobre impuestos"

def test_mastery_update():
    # Correct adds points
    assert calculate_mastery_update(True, 50.0) > 50.0
    # Incorrect penalties
    assert calculate_mastery_update(False, 50.0) < 50.0
    # Caps
    assert calculate_mastery_update(True, 100.0) == 100.0
    assert calculate_mastery_update(False, 0.0) == 0.0
