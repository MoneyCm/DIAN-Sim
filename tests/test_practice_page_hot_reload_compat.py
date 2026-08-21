from pathlib import Path


PRACTICE_PAGE = (
    Path(__file__).resolve().parents[1] / "app" / "pages" / "1_Nuevo_Simulacro.py"
)


def test_practice_page_does_not_require_new_function_coverage_exports_at_runtime():
    source = PRACTICE_PAGE.read_text(encoding="utf-8")

    assert "from core.function_coverage import function_display_detail" not in source
    assert "from core.function_coverage import function_display_label" not in source
    assert 'getattr(function_coverage_utils, "function_display_detail", None)' in source
    assert 'getattr(function_coverage_utils, "function_display_label", None)' in source
