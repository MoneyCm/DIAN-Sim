from pathlib import Path


def test_menu_prioritizes_daily_actions_and_hides_execution_page():
    source = Path("app/app.py").read_text(encoding="utf-8")
    assert '"Inicio": [p_dashboard]' in source
    assert '"Mi preparación"' in source
    assert '"Mi progreso": [p_resultados]' in source
    assert '"Más opciones"' in source
    assert '"Herramientas de administración"' in source
    assert "p_ejecucion" not in source.split("pages = {", 1)[1].split("# Determinar", 1)[0]


def test_dashboard_exposes_the_three_primary_actions():
    source = Path("app/pages/6_Dashboard.py").read_text(encoding="utf-8")
    assert "¿Qué quieres hacer hoy?" in source
    assert "Empezar práctica" in source
    assert "Ver mi plan" in source
    assert "Cambiar OPEC" in source
