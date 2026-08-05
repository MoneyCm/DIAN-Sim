"""Extraction of OPEC employment data from an uploaded PDF."""

from __future__ import annotations

from io import BytesIO
import re

from pypdf import PdfReader


def extract_opec_profile(pdf_bytes: bytes) -> dict[str, str | list[str]]:
    """Extract a profile from a text-based PDF (legacy upload support)."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError("No fue posible leer el PDF. Verifica que no esté protegido o dañado.") from exc

    return extract_opec_profile_from_text(text)


def extract_opec_profile_from_text(text: str) -> dict[str, str | list[str]]:
    """Extract the standard SIMO/OPEC labels from pasted employment text."""
    if len(text.strip()) < 40:
        raise ValueError("Pega el texto completo de la ficha de empleo de SIMO.")

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
        "denomination": field(r"(?:Denominaci[oó]n|Nombre\s+del\s+Cargo)\s*:?[ \t]*(.*?)(?=\s+(?:Grado|C[oó]digo)\s*:|\n)"),
        "code": field(r"C[oó]digo\s*:?[ \t]*(\d+)"),
        "grade": field(r"Grado\s*:?[ \t]*(\d+)"),
        "level": field(r"Nivel\s*:?[ \t]*(.*?)(?=\s+(?:Denominaci[oó]n|Nombre\s+del\s+Cargo)\s*:|\n)"),
        "purpose": re.sub(r"\s+", " ", section(r"Prop[oó]sito", r"Funciones|Requisitos|Equivalencias")).strip(),
        "functions": functions,
        "requirements": re.sub(r"\s+", " ", section(r"Requisitos", r"Equivalencias|Vacantes")).strip(),
    }
    profile["job_title"] = " ".join(
        part for part in [str(profile["denomination"]), f"Grado {profile['grade']}" if profile["grade"] else ""] if part
    )
    if not profile["job_title"] and profile["opec_number"]:
        profile["job_title"] = f"Empleo OPEC {profile['opec_number']}"
    return profile
