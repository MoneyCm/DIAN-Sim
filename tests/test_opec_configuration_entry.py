from pathlib import Path


def test_navigation_separates_active_opec_selection_from_technical_tools():
    app_source = Path("app/app.py").read_text(encoding="utf-8")
    page_source = Path("app/pages/15_Centro_OPEC.py").read_text(encoding="utf-8")
    assert 'pages/15_Centro_OPEC.py' in app_source
    assert 'title="Herramientas OPEC"' in app_source
    assert 'pages/14_Mis_OPEC.py' in page_source
    assert "La OPEC activa controla tus prácticas" in page_source
