"""Profiles stored locally so a competition can be reused without hard-coding it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from db.models import Competition


CATALOG_ROOT = Path(__file__).resolve().parents[1] / "data" / "concursos"


def load_catalog_profiles() -> list[dict[str, Any]]:
    """Return valid profiles from ``data/concursos`` without breaking the UI."""
    profiles: list[dict[str, Any]] = []
    for path in sorted(CATALOG_ROOT.glob("*/perfil_concurso.json")):
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
            competition = profile["competition"]
            position = profile["position"]
            if competition.get("code") and competition.get("name") and position.get("opec_number"):
                profile["_path"] = str(path)
                profiles.append(profile)
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            continue
    return profiles


def sync_catalog_competitions(db) -> None:
    """Create missing competition rows from local profiles."""
    for profile in load_catalog_profiles():
        source = profile["competition"]
        if not db.query(Competition).filter_by(code=source["code"]).first():
            db.add(Competition(
                code=source["code"],
                name=source["name"],
                entity=source.get("entity"),
                description=f"Perfil local: {profile['_path']}",
                is_active=True,
            ))


def profile_for_competition(profiles: list[dict[str, Any]], code: str | None) -> dict[str, Any] | None:
    return next((p for p in profiles if p["competition"]["code"] == code), None)


def profile_requirements_text(profile: dict[str, Any]) -> str:
    requirements = profile.get("requirements", {})
    lines = [f"Estudio: {item}" for item in requirements.get("education", [])]
    if requirements.get("experience"):
        lines.append(f"Experiencia: {requirements['experience']}")
    if requirements.get("other"):
        lines.append(f"Otros: {requirements['other']}")
    return "\n".join(lines)
