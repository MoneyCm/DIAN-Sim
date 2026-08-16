from streamlit.testing.v1 import AppTest


def test_app_entrypoint_builds_navigation_and_login_without_exception():
    app = AppTest.from_file("app/app.py", default_timeout=30).run()

    assert not app.exception
    assert any("Acceso al Simulador" in str(item.value) for item in app.markdown)
    assert any("Iniciar Sesión" in str(item.value) for item in app.subheader)
