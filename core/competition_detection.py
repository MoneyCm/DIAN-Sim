"""Detección del proceso de selección incluido en una ficha copiada de SIMO."""

import re
import unicodedata


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" .,-")


def competition_code_from_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.upper())
    ascii_name = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", "-", ascii_name).strip("-")[:80]


def detect_competition_from_simo(text: str):
    """Devuelve nombre, entidad y código estable cuando la cabecera los contiene."""
    match = re.search(
        r"Vigencia\s+salarial\s*:\s*\d{4}\s+(.*?)(?=Cierre\s+de\s+inscripciones)",
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    name = _clean(match.group(1))
    if not name:
        return None
    entity = _clean(re.split(r"\s+-\s+", name, maxsplit=1)[0])
    return {"name": name, "entity": entity, "code": competition_code_from_name(name)}


def competition_matches(detected: dict | None, *, selected_name: str, selected_entity: str = ""):
    if not detected:
        return True
    haystack = f"{selected_name} {selected_entity}".upper()
    return detected["entity"].upper() in haystack or detected["name"].upper() in haystack
