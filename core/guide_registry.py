"""Versioned registry for competition guides and thematic sources."""

import json
from pathlib import Path


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "competition_guides.json"


def guide_status(competition_code: str) -> dict:
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        registry = {}
    return registry.get(competition_code, {
        "status": "unregistered",
        "label": "Fuentes oficiales pendientes de registrar",
        "version": "unversioned",
        "official_sources": [],
        "next_action": "Registrar la guía oficial y reconstruir la matriz temática.",
    })
