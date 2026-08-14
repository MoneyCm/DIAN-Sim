from pathlib import Path


def test_navigation_uses_unique_page_paths_for_configuration_and_tools():
    source = Path("app/app.py").read_text(encoding="utf-8")
    assert 'p_config = st.Page("pages/15_Centro_OPEC.py"' in source
    assert 'p_opec_tools = st.Page("pages/7_Configuracion_OPEC.py"' in source
