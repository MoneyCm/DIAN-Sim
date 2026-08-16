from pathlib import Path


def test_sensitive_pages_enforce_database_backed_admin_guard():
    for page in ("app/pages/4_Generador_IA.py", "app/pages/8_Panel_Admin.py"):
        source = Path(page).read_text(encoding="utf-8")
        assert "from core.access_control import require_admin" in source
        assert "require_admin()" in source


def test_admin_pdf_upload_uses_content_validation_and_atomic_write():
    source = Path("app/pages/8_Panel_Admin.py").read_text(encoding="utf-8")
    assert "sanitize_upload_name(" in source
    assert "validate_pdf(payload)" in source
    assert "atomic_write(destination, payload)" in source
    assert ".write_bytes(uploaded_file.getbuffer())" not in source


def test_admin_ai_batches_have_explicit_hard_caps():
    source = Path("app/pages/8_Panel_Admin.py").read_text(encoding="utf-8")
    assert 'max_value=50' in source
    assert 'max_value=25' in source
    assert "reserve_ai_usage(" in source


def test_streamlit_rejects_oversize_requests_and_enables_request_protection():
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8")
    assert "enableCORS = true" in config
    assert "enableXsrfProtection = true" in config
    assert "maxUploadSize = 10" in config
