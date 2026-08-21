import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sidebar_calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_custom_sidebar"
    ]


def test_entrypoint_is_the_only_sidebar_renderer():
    entrypoint = ROOT / "app" / "app.py"
    pages = sorted((ROOT / "app" / "pages").glob("*.py"))

    assert len(_sidebar_calls(entrypoint)) == 1
    assert {
        page.name: len(_sidebar_calls(page))
        for page in pages
        if _sidebar_calls(page)
    } == {}


def test_sidebar_page_links_render_after_navigation_registration():
    source = (ROOT / "app" / "app.py").read_text(encoding="utf-8-sig")
    sidebar_call = source.index("render_custom_sidebar()")

    assert sidebar_call > source.index('st.navigation({"Primeros pasos": onboarding_pages})')
    assert sidebar_call > source.index("st.navigation(pages)")
