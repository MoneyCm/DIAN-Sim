from pathlib import Path


def test_app_navigation_guards_a_new_page_during_cloud_source_refresh():
    source = Path("app/app.py").read_text(encoding="utf-8")
    assert 'mis_opec_page_path = os.path.join(APP_DIR, "pages", "14_Mis_OPEC.py")' in source
    assert "if os.path.isfile(mis_opec_page_path)" in source
    assert "if p_mis_opec is not None:" in source
