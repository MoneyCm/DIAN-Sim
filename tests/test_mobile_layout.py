from pathlib import Path


def test_app_uses_responsive_sidebar_and_mobile_touch_layout():
    app_source = Path("app/app.py").read_text(encoding="utf-8-sig")
    css = Path("app/styles.css").read_text(encoding="utf-8")

    assert 'initial_sidebar_state="auto"' in app_source
    assert "@media (max-width: 768px)" in css
    assert "min-height: 44px" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
    assert 'data-testid="stDataFrame"' in css
