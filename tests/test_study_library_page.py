from pathlib import Path


PAGE = Path("app/pages/16_Biblioteca_Estudio.py").read_text(encoding="utf-8")
APP = Path("app/app.py").read_text(encoding="utf-8")
DASHBOARD = Path("app/pages/6_Dashboard.py").read_text(encoding="utf-8")


def test_library_is_registered_as_a_secondary_action_not_a_primary_destination():
    assert 'p_study_library = st.Page("pages/16_Biblioteca_Estudio.py"' in APP
    assert "p_study_map, p_study_library, p_etica" in APP
    assert "pages/16_Biblioteca_Estudio.py" in DASHBOARD


def test_library_uses_active_opec_and_training_scope_only():
    assert "get_active_opec(db, user_id)" in PAGE
    assert "user_opec_id=active_opec.id" in PAGE
    assert 'bank_partitions=("training",)' in PAGE


def test_library_does_not_misrepresent_editorial_sources_or_invent_locators():
    assert "no están publicados" in PAGE
    assert "Corpus recomendado" in PAGE
    assert "confirmarse antes de usarlo" in PAGE
    assert "no los completa por inferencia" in PAGE


def test_mastery_cannot_be_selected_manually():
    assert 'EDITABLE_STATES = ("not_started", "studying", "read", "reviewed")' in PAGE
    assert "Dominado con evidencia" in PAGE
