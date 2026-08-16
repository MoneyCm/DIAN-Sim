from pathlib import Path


PAGE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "pages" / "13_Tutor_Adaptativo.py"
)


def test_tutor_requires_reasoning_and_preserves_offline_route():
    source = PAGE_PATH.read_text(encoding="utf-8-sig")

    assert "Explica brevemente por qué elegiste esa opción" in source
    assert "user_reasoning=reasoning" in source
    assert "motor local determinista; no requiere clave de IA" in source
    assert "TutorService(ModelRouter" in source


def test_tutor_distinguishes_verified_source_from_generated_orientation():
    source = PAGE_PATH.read_text(encoding="utf-8-sig")

    assert "has_precise_source_verification" in source
    assert "Fuente verificada" in source
    assert "Fuente declarada pendiente" in source
    assert "Excepción normativa: no se inventa" in source
