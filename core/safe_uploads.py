"""Bounded, content-aware handling for documents uploaded by administrators.

Streamlit's ``type=`` filter is a user-interface convenience, not a security
boundary.  These helpers validate the bytes again before they are parsed or
persisted and keep filenames confined to the intended directory.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import os
from pathlib import Path
import re
import tempfile
import unicodedata

import pypdf


class UnsafeUpload(ValueError):
    """A document is invalid or exceeds the application's safe limits."""


@dataclass(frozen=True)
class DocumentLimits:
    max_pdf_bytes: int = 10 * 1024 * 1024
    max_text_bytes: int = 2 * 1024 * 1024
    max_pdf_pages: int = 400
    max_extracted_chars: int = 2_000_000
    max_filename_chars: int = 120


DEFAULT_DOCUMENT_LIMITS = DocumentLimits()
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def _as_bytes(payload: object) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    if isinstance(payload, memoryview):
        return payload.tobytes()
    raise UnsafeUpload("El archivo recibido no tiene un formato binario válido.")


def sanitize_upload_name(
    raw_name: object,
    *,
    allowed_suffixes: tuple[str, ...],
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> str:
    """Return a harmless basename while preserving only an allowed suffix."""
    normalized = unicodedata.normalize("NFKC", str(raw_name or "")).replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1].strip().strip(".")
    suffix = Path(basename).suffix.lower()
    allowed = tuple(item.lower() for item in allowed_suffixes)
    if suffix not in allowed:
        raise UnsafeUpload("La extensión del archivo no está permitida.")

    stem = basename[: -len(suffix)] if suffix else basename
    stem = re.sub(r"[^\w .-]+", "_", stem, flags=re.UNICODE)
    stem = re.sub(r"[ ._-]+", "_", stem).strip("_")
    if not stem:
        raise UnsafeUpload("El archivo necesita un nombre válido.")
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"documento_{stem.lower()}"

    room = max(limits.max_filename_chars - len(suffix), 1)
    return f"{stem[:room]}{suffix}"


def confined_destination(root: str | os.PathLike[str], filename: str) -> Path:
    """Resolve a destination and prove it remains immediately under ``root``."""
    base = Path(root).resolve()
    destination = (base / filename).resolve()
    if destination.parent != base:
        raise UnsafeUpload("La ruta del archivo no es segura.")
    return destination


def validate_pdf(
    payload: object,
    *,
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> pypdf.PdfReader:
    data = _as_bytes(payload)
    if not data:
        raise UnsafeUpload("El PDF está vacío.")
    if len(data) > limits.max_pdf_bytes:
        raise UnsafeUpload(
            f"El PDF supera el límite seguro de {limits.max_pdf_bytes // (1024 * 1024)} MB."
        )
    if b"%PDF-" not in data[:1024]:
        raise UnsafeUpload("El contenido no corresponde a un PDF válido.")

    try:
        reader = pypdf.PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise UnsafeUpload("No se admiten PDF protegidos con contraseña.")
        page_count = len(reader.pages)
    except UnsafeUpload:
        raise
    except Exception as exc:
        raise UnsafeUpload("El PDF está dañado o no se puede leer de forma segura.") from exc

    if page_count < 1:
        raise UnsafeUpload("El PDF no contiene páginas.")
    if page_count > limits.max_pdf_pages:
        raise UnsafeUpload(
            f"El PDF supera el límite seguro de {limits.max_pdf_pages} páginas."
        )
    return reader


def extract_pdf_pages(
    payload: object,
    *,
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> list[str]:
    """Extract bounded text per page; reject instead of silently truncating."""
    reader = validate_pdf(payload, limits=limits)
    pages: list[str] = []
    total_chars = 0
    try:
        for page in reader.pages:
            text = page.extract_text() or ""
            total_chars += len(text)
            if total_chars > limits.max_extracted_chars:
                raise UnsafeUpload(
                    "El texto extraído supera el límite seguro para un solo documento."
                )
            pages.append(text)
    except UnsafeUpload:
        raise
    except Exception as exc:
        raise UnsafeUpload("No fue posible extraer el texto del PDF de forma segura.") from exc
    return pages


def extract_text_file(
    payload: object,
    *,
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> str:
    data = _as_bytes(payload)
    if not data:
        raise UnsafeUpload("El archivo de texto está vacío.")
    if len(data) > limits.max_text_bytes:
        raise UnsafeUpload(
            f"El TXT supera el límite seguro de {limits.max_text_bytes // (1024 * 1024)} MB."
        )
    if b"\x00" in data:
        raise UnsafeUpload("El archivo no parece ser texto plano.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsafeUpload("El TXT debe estar codificado en UTF-8.") from exc
    if len(text) > limits.max_extracted_chars:
        raise UnsafeUpload("El texto supera el límite seguro para un solo documento.")
    return text


def atomic_write(destination: Path, payload: object) -> None:
    """Persist validated bytes atomically and never replace an existing file."""
    data = _as_bytes(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=".upload-", suffix=".tmp", delete=False
        ) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        try:
            # A same-filesystem hard link publishes the complete temporary file
            # as one directory operation and, unlike rename/replace, fails when
            # the destination appeared after the UI's existence check.
            os.link(temp_path, destination)
        except FileExistsError as exc:
            raise UnsafeUpload(
                "Ya existe un documento con ese nombre; no se reemplazó el archivo."
            ) from exc
        temp_path.unlink()
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
