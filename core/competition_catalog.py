"""Profiles stored locally so a competition can be reused without hard-coding it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import unicodedata

from db.models import CaseStudy, Competition, Question, Skill, StudyPlanConfig, UserOPEC


CATALOG_ROOT = Path(__file__).resolve().parents[1] / "data" / "concursos"


def _normalized_name(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFD", value.upper())
        if unicodedata.category(character) != "Mn"
    )


def is_hidden_catalog_duplicate(competition: Competition, profiles: list[dict[str, Any]]) -> bool:
    """Hide legacy manual entries when a canonical catalogue profile exists."""
    normalized = _normalized_name(competition.name)
    for profile in profiles:
        source = profile["competition"]
        if competition.code == source["code"]:
            continue
        if source["code"] == "TERRITORIAL-12-BOLIVAR-2685":
            if "TERRITORIAL 12" in normalized and "BOLIVAR" in normalized:
                return True
    return False


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
    """Create catalogued competitions and merge their legacy duplicates safely."""
    for profile in load_catalog_profiles():
        source = profile["competition"]
        canonical = db.query(Competition).filter_by(code=source["code"]).first()
        if not canonical:
            canonical = Competition(
                code=source["code"],
                name=source["name"],
                entity=source.get("entity"),
                description=f"Perfil local: {profile['_path']}",
                is_active=True,
            )
            db.add(canonical)
            db.flush()

        # Earlier versions allowed entering the same Territorial 12 process
        # manually. Merge only the exact Bolívar process; other Territorial 12
        # entities must remain distinct competitions.
        duplicate_candidates = [
            competition for competition in db.query(Competition).all()
            if competition.id != canonical.id
            and "TERRITORIAL 12" in _normalized_name(competition.name)
            and "BOLIVAR" in _normalized_name(competition.name)
        ]
        for duplicate in duplicate_candidates:
            for model in (UserOPEC, StudyPlanConfig, CaseStudy, Question, Skill):
                db.query(model).filter(model.competition_id == duplicate.id).update(
                    {model.competition_id: canonical.id}, synchronize_session=False
                )
            db.delete(duplicate)


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
