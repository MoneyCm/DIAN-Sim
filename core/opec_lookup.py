"""Lookup of reusable public OPEC job profiles by number."""

from __future__ import annotations

import re

from db.models import Competition, UserOPEC


def normalize_opec_number(value: object) -> str:
    return "".join(re.findall(r"\d", str(value or "")))


def _is_complete(row: UserOPEC) -> bool:
    return bool(
        str(row.job_title or "").strip()
        and str(row.purpose or "").strip()
        and list(row.functions or [])
        and str(row.requirements or "").strip()
    )


def find_reusable_opec(db, opec_number: object) -> dict | None:
    """Return only public employment fields; never expose the source user."""
    number = normalize_opec_number(opec_number)
    if len(number) < 4:
        return None
    rows = (
        db.query(UserOPEC)
        .filter(UserOPEC.opec_number == number)
        .order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc())
        .all()
    )
    row = next((candidate for candidate in rows if _is_complete(candidate)), None)
    if row is None:
        # A canonical profile can be reused before any individual user has
        # saved it. This avoids asking each aspirant to paste the same public
        # SIMO employment sheet.
        from core.competition_catalog import load_catalog_profiles, profile_requirements_text

        profile = next(
            (
                item for item in load_catalog_profiles()
                if normalize_opec_number(item.get("position", {}).get("opec_number")) == number
            ),
            None,
        )
        if profile is None:
            return None
        source_competition = profile["competition"]
        competition = db.query(Competition).filter_by(code=source_competition["code"]).first()
        return {
            "opec_number": number,
            "job_title": profile["position"].get("denomination") or f"Empleo OPEC {number}",
            "level": profile["position"].get("level"),
            "purpose": profile.get("purpose") or "",
            "functions": list(profile.get("functions") or []),
            "requirements": profile_requirements_text(profile),
            "competition": {
                "id": competition.id if competition else None,
                "code": source_competition["code"],
                "name": source_competition["name"],
                "entity": source_competition.get("entity"),
            },
            "catalog_status": "perfil_oficial_preconfigurado",
        }
    competition = db.get(Competition, row.competition_id) if row.competition_id else None
    return {
        "opec_number": number,
        "job_title": row.job_title,
        "level": row.level,
        "purpose": row.purpose,
        "functions": list(row.functions or []),
        "requirements": row.requirements,
        "competition": {
            "id": competition.id if competition else None,
            "code": competition.code if competition else None,
            "name": competition.name if competition else "Concurso por confirmar",
            "entity": competition.entity if competition else None,
        },
        "catalog_status": "reutilizable_pendiente_confirmacion",
    }


def attach_reusable_opec_to_user(db, user_id: int, profile: dict) -> UserOPEC:
    """Attach a public profile to a user without copying source-user identity."""
    number = normalize_opec_number(profile.get("opec_number"))
    if not number:
        raise ValueError("Número OPEC inválido")
    db.query(UserOPEC).filter_by(user_id=user_id).update(
        {UserOPEC.is_active: False}, synchronize_session=False
    )
    row = (
        db.query(UserOPEC)
        .filter_by(user_id=user_id, opec_number=number)
        .order_by(UserOPEC.updated_at.desc())
        .first()
    )
    values = {
        "competition_id": profile.get("competition", {}).get("id"),
        "job_title": profile.get("job_title") or f"Empleo OPEC {number}",
        "level": profile.get("level"),
        "purpose": profile.get("purpose"),
        "functions": list(profile.get("functions") or []),
        "requirements": profile.get("requirements"),
        "is_active": True,
    }
    if row is None:
        row = UserOPEC(user_id=user_id, opec_number=number, **values)
        db.add(row)
    else:
        for field, value in values.items():
            setattr(row, field, value)
    return row
