from pathlib import Path


PAGE_PATH = Path(__file__).resolve().parents[1] / "app" / "pages" / "6_Dashboard.py"


def test_resume_is_visible_before_quick_dashboard_stop():
    source = PAGE_PATH.read_text(encoding="utf-8-sig")
    resume_position = source.index("Reanudar práctica pendiente")
    quick_stop_position = source.index('if not show_advanced_dashboard:')

    assert resume_position < quick_stop_position
    assert "competition_id=active_competition_id" in source[resume_position - 900:resume_position]
    assert "opec_number=active_opec.opec_number" in source[resume_position - 900:resume_position]
    assert 'st.switch_page("pages/2_Ejecucion.py")' in source[resume_position:resume_position + 500]
