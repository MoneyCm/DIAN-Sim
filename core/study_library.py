"""OPEC-scoped study library built from registered official sources."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable

from core.preparation_matrix import load_preparation_blueprint
from db.models import Configuration, UserOPEC


LIBRARY_POLICY_VERSION = "study-library-internal-v1"
PROGRESS_STATES = (
    "not_started",
    "studying",
    "read",
    "reviewed",
    "mastered",
)
PROGRESS_LABELS = {
    "not_started": "No iniciado",
    "studying": "En estudio",
    "read": "Leído",
    "reviewed": "Repasado",
    "mastered": "Dominado con evidencia",
}
CORE_SOURCE_IDS = {
    "agreement_21_2025",
    "annex_2676_2025",
    "pjs_spec_lp004_2026",
    "profile_at_fl_3006",
    "resolution_67_2024",
    "resolution_66_2024",
    "resolution_65_2024",
    "behavioral_dictionary_65_2024",
}


@dataclass(frozen=True)
class StudyDocument:
    source_id: str
    name: str
    entity: str
    url: str
    date_version: str
    consulted_on: str
    validity: str
    source_status: str
    relationship: str
    priority: str
    estimated_minutes: int
    function_numbers: tuple[int, ...]
    topics: tuple[str, ...]
    locator: str | None
    locator_precise: bool
    pedagogical_summary: str
    main_rule: str | None
    exception: str | None
    work_example: str | None
    associated_question_count: int


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def precise_locator(locator: object) -> bool:
    text = _normalise(locator)
    if not text:
        return False
    vague = (
        "artículos aplicables",
        "articulo aplicable",
        "artículo aplicable",
        "por caso",
        "cada pregunta",
        "documento completo",
        "artículo reglamentario aplicable",
        "disposiciones aplicables",
    )
    return not any(marker in text for marker in vague)


def _question_count(source: dict, question_source_refs: Iterable[str]) -> int:
    url = _normalise(source.get("url"))
    name = _normalise(source.get("name"))
    source_id = _normalise(source.get("id"))
    count = 0
    for raw in question_source_refs or ():
        reference = _normalise(raw)
        if not reference:
            continue
        if (url and url in reference) or (name and name in reference) or (
            source_id and source_id in reference
        ):
            count += 1
    return count


def build_study_library(
    opec_number: object,
    *,
    question_source_refs: Iterable[str] = (),
) -> tuple[StudyDocument, ...]:
    blueprint = load_preparation_blueprint(opec_number)
    if not blueprint:
        return ()
    functions_by_source: dict[str, set[int]] = {}
    for function in blueprint.get("functions", []) or []:
        number = int(function.get("number", 0) or 0)
        for source_id in function.get("source_ids", []) or []:
            functions_by_source.setdefault(str(source_id), set()).add(number)

    items = []
    for source in blueprint.get("sources", []) or []:
        source_id = str(source.get("id", "")).strip()
        linked_functions = tuple(sorted(functions_by_source.get(source_id, set())))
        if not linked_functions and source_id not in CORE_SOURCE_IDS:
            continue
        relationship = (
            "Base oficial del proceso o del empleo"
            if source_id in CORE_SOURCE_IDS
            else "Corpus oficial relacionado por la matriz editorial; no es temario oficial publicado"
        )
        if source_id in CORE_SOURCE_IDS or len(linked_functions) >= 5:
            priority = "Alta"
        elif len(linked_functions) >= 2:
            priority = "Media"
        else:
            priority = "Baja"
        topics = tuple(str(item) for item in source.get("topics", []) if str(item).strip())
        locator = str(source.get("locators", "")).strip() or None
        summary = (
            "Apoya: " + ", ".join(topics)
            if topics
            else "Resumen pedagógico pendiente de curaduría contra el documento oficial."
        )
        items.append(
            StudyDocument(
                source_id=source_id,
                name=str(source.get("name", "Documento oficial")),
                entity=str(source.get("entity", "Entidad no registrada")),
                url=str(source.get("url", "")),
                date_version=str(source.get("date_version", "")),
                consulted_on=str(source.get("consulted_on", "")),
                validity=str(source.get("validity", "Vigencia pendiente")),
                source_status=str(source.get("status", "pending")),
                relationship=relationship,
                priority=priority,
                estimated_minutes=min(90, 20 + 5 * max(len(linked_functions), 1)),
                function_numbers=linked_functions,
                topics=topics,
                locator=locator,
                locator_precise=precise_locator(locator),
                pedagogical_summary=summary,
                main_rule=None,
                exception=None,
                work_example=None,
                associated_question_count=_question_count(source, question_source_refs),
            )
        )
    priority_rank = {"Alta": 0, "Media": 1, "Baja": 2}
    return tuple(
        sorted(items, key=lambda item: (priority_rank[item.priority], item.name))
    )


def _progress_key(
    *, user_id: int, competition_id: int, user_opec_id: int, opec_number: object
) -> str:
    return (
        f"study_library_progress:{int(user_id)}:competition:{int(competition_id)}:"
        f"user_opec:{int(user_opec_id)}:opec:{str(opec_number).strip()}"
    )


def _validate_scope(
    db, *, user_id: int, competition_id: int, user_opec_id: int, opec_number: object
) -> UserOPEC:
    row = db.get(UserOPEC, int(user_opec_id))
    if (
        row is None
        or row.user_id != int(user_id)
        or row.competition_id != int(competition_id)
        or str(row.opec_number).strip() != str(opec_number).strip()
    ):
        raise ValueError("El progreso de biblioteca no coincide con la OPEC del usuario.")
    return row


def load_library_progress(
    db, *, user_id: int, competition_id: int, user_opec_id: int, opec_number: object
) -> dict[str, str]:
    _validate_scope(
        db,
        user_id=user_id,
        competition_id=competition_id,
        user_opec_id=user_opec_id,
        opec_number=opec_number,
    )
    row = db.query(Configuration).filter_by(
        key_name=_progress_key(
            user_id=user_id,
            competition_id=competition_id,
            user_opec_id=user_opec_id,
            opec_number=opec_number,
        )
    ).first()
    if row is None:
        return {}
    try:
        payload = json.loads(row.value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("policy_version") != LIBRARY_POLICY_VERSION:
        return {}
    statuses = payload.get("statuses")
    if not isinstance(statuses, dict):
        return {}
    return {
        str(source_id): str(status)
        for source_id, status in statuses.items()
        if str(status) in PROGRESS_STATES
    }


def save_library_status(
    db,
    *,
    user_id: int,
    competition_id: int,
    user_opec_id: int,
    opec_number: object,
    source_id: str,
    status: str,
    verified_mastery: bool = False,
) -> dict[str, str]:
    if status not in PROGRESS_STATES:
        raise ValueError("Estado de lectura no válido.")
    if status == "mastered" and not verified_mastery:
        raise ValueError("Dominado exige evidencia de aprendizaje; no se marca manualmente.")
    progress = load_library_progress(
        db,
        user_id=user_id,
        competition_id=competition_id,
        user_opec_id=user_opec_id,
        opec_number=opec_number,
    )
    progress[str(source_id)] = status
    key = _progress_key(
        user_id=user_id,
        competition_id=competition_id,
        user_opec_id=user_opec_id,
        opec_number=opec_number,
    )
    row = db.query(Configuration).filter_by(key_name=key).first()
    if row is None:
        row = Configuration(key_name=key, value="{}")
        db.add(row)
    row.value = json.dumps(
        {"policy_version": LIBRARY_POLICY_VERSION, "statuses": progress},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    db.commit()
    return progress
