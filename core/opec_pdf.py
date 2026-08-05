"""Extraction of OPEC employment data from an uploaded PDF."""

from __future__ import annotations

from io import BytesIO
import re

from pypdf import PdfReader


def extract_opec_profile(pdf_bytes: bytes) -> dict[str, str | list[str]]:
    """Extract the standard SIMO/OPEC labels from a text-based PDF.

    The caller must present the extracted values for confirmation. Scanned PDFs
    have no usable text layer and deliberately raise a clear error instead of
    inventing a profile.
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError("No fue posible leer el PDF. Verifica que no esté protegido o dañado.") from exc

    if len(text.strip()) < 80:
        raise ValueError("El PDF no contiene texto seleccionable. Sube el PDF original de SIMO, no una imagen escaneada.")

    def field(pattern: str) -> str:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""

    def section(start: str, end: str) -> str:
        match = re.search(
            rf"{start}\s*[:\-]?\s*(.*?)(?=\s*{end}\b|\Z)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return match.group(1).strip() if match else ""

    functions_raw = section(r"Funciones", r"Requisitos|Equivalencias|Vacantes")
    function_matches = re.findall(
        r"(?:^|\n)\s*(\d{1,2})\s*[\.)]\s*(.*?)(?=(?:\n\s*\d{1,2}\s*[\.)])|\Z)",
        functions_raw,
        flags=re.DOTALL,
    )
    functions = [re.sub(r"\s+", " ", body).strip() for _, body in function_matches if body.strip()]
    if not functions and functions_raw:
        functions = [re.sub(r"\s+", " ", functions_raw).strip()]

    profile: dict[str, str | list[str]] = {
        "opec_number": field(r"(?:N[uú]mero\s+)?OPEC\s*[:#]?\s*(\d{4,})"),
        "denomination": field(r"Denominaci[oó]n\s*:\s*(.*?)(?=\s+(?:Grado|C[oó]digo)\s*:|\n)"),
        "code": field(r"C[oó]digo\s*:\s*(\d+)"),
        "grade": field(r"Grado\s*:\s*(\d+)"),
        "level": field(r"Nivel\s*:\s*(.*?)(?=\s+Denominaci[oó]n\s*:|\n)"),
        "purpose": re.sub(r"\s+", " ", section(r"Prop[oó]sito", r"Funciones|Requisitos|Equivalencias")).strip(),
        "functions": functions,
        "requirements": re.sub(r"\s+", " ", section(r"Requisitos", r"Equivalencias|Vacantes")).strip(),
    }
    profile["job_title"] = " ".join(
        part for part in [str(profile["denomination"]), f"Grado {profile['grade']}" if profile["grade"] else ""] if part
    )
    return profile
