import io

import pytest
from pypdf import PdfWriter

from core.safe_uploads import (
    DocumentLimits,
    UnsafeUpload,
    atomic_write,
    confined_destination,
    extract_text_file,
    sanitize_upload_name,
    validate_pdf,
)


def _one_page_pdf() -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    return output.getvalue()


def test_upload_filename_is_confined_and_sanitized(tmp_path):
    name = sanitize_upload_name(
        r"..\..\guía<script>.PDF", allowed_suffixes=(".pdf",)
    )
    assert name == "guía_script.pdf"
    destination = confined_destination(tmp_path, name)
    assert destination.parent == tmp_path.resolve()


def test_pdf_validation_checks_content_not_only_extension():
    with pytest.raises(UnsafeUpload, match="no corresponde"):
        validate_pdf(b"not a pdf")


def test_pdf_validation_enforces_size_and_page_limits():
    payload = _one_page_pdf()
    assert len(validate_pdf(payload).pages) == 1
    with pytest.raises(UnsafeUpload, match="MB"):
        validate_pdf(
            payload,
            limits=DocumentLimits(max_pdf_bytes=10, max_pdf_pages=10),
        )
    with pytest.raises(UnsafeUpload, match="páginas"):
        validate_pdf(
            payload,
            limits=DocumentLimits(max_pdf_bytes=10_000, max_pdf_pages=0),
        )


def test_text_upload_rejects_binary_and_oversize_content():
    with pytest.raises(UnsafeUpload, match="texto plano"):
        extract_text_file(b"abc\x00def")
    with pytest.raises(UnsafeUpload, match="TXT supera"):
        extract_text_file(
            b"abcdefgh",
            limits=DocumentLimits(max_text_bytes=4),
        )


def test_atomic_write_persists_only_to_resolved_destination(tmp_path):
    destination = confined_destination(tmp_path, "norma.pdf")
    atomic_write(destination, b"validated")
    assert destination.read_bytes() == b"validated"
    with pytest.raises(UnsafeUpload, match="no se reemplazó"):
        atomic_write(destination, b"replacement")
    assert destination.read_bytes() == b"validated"
    assert not list(tmp_path.glob(".upload-*.tmp"))
