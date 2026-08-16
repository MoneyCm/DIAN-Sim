"""Explainable daily study recommendations for one OPEC.

The recommendations use the versioned preparation matrix and observed local
evidence.  They never turn editorial targets into official exam weights and
never invent an article/page when the source matrix lacks an exact locator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Mapping

from core.preparation_matrix import load_preparation_blueprint
from core.study_planner import build_timed_session, days_until_exam, preparation_phase


INTERNAL_POLICY_VERSION = "study-plan-internal-v1"


@dataclass(frozen=True)
class FunctionEvidence:
    function_number: int
    mastery_score: float = 0.0
    attempts: int = 0
    trusted_question_count: int = 0
    due_error_count: int = 0
    delayed_retention_rate: float | None = None
    question_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StudySource:
    source_id: str
    name: str
    url: str
    locator: str | None
    locator_verified: bool
    validity: str


@dataclass(frozen=True)
class StudyActivitySpec:
    activity_type: str
    minutes: int
    instruction: str


@dataclass(frozen=True)
class DailyStudyMission:
    opec_number: str
    function_number: int
    function_name: str
    topic: str
    total_minutes: int
    question_goal: int
    target_score: float
    target_status: str
    reason: str
    source: StudySource | None
    activities: tuple[StudyActivitySpec, ...]
    question_ids: tuple[str, ...]
    days_remaining: int | None
    phase: str
    policy_version: str = INTERNAL_POLICY_VERSION


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(float(value), low), high)


def _function_priority(evidence: FunctionEvidence, target_questions: int) -> float:
    mastery_gap = 1.0 - _clamp(evidence.mastery_score, 0.0, 100.0) / 100.0
    coverage_gap = 1.0 - min(
        max(int(evidence.trusted_question_count or 0), 0) / max(int(target_questions or 1), 1),
        1.0,
    )
    insufficient_evidence = 1.0 if int(evidence.attempts or 0) < 5 else 0.0
    overdue = min(max(int(evidence.due_error_count or 0), 0) / 5.0, 1.0)
    retention_gap = (
        0.5
        if evidence.delayed_retention_rate is None
        else 1.0 - _clamp(evidence.delayed_retention_rate, 0.0, 1.0)
    )
    return round(
        0.35 * mastery_gap
        + 0.25 * coverage_gap
        + 0.15 * insufficient_evidence
        + 0.15 * overdue
        + 0.10 * retention_gap,
        6,
    )


def _has_precise_locator(locator: object) -> bool:
    text = str(locator or "").strip().lower()
    if not text:
        return False
    vague = (
        "aplicable",
        "cada pregunta",
        "por caso",
        "artículo reglamentario",
        "documento completo",
    )
    return not any(marker in text for marker in vague)


def _pick_source(function: Mapping, source_by_id: Mapping[str, Mapping]) -> StudySource | None:
    candidates = [
        source_by_id[source_id]
        for source_id in function.get("source_ids", [])
        if source_id in source_by_id
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            not _has_precise_locator(item.get("locators")),
            item.get("status") not in {"official_verified", "official_available"},
            str(item.get("name", "")),
        )
    )
    source = candidates[0]
    precise = _has_precise_locator(source.get("locators"))
    return StudySource(
        source_id=str(source.get("id", "")),
        name=str(source.get("name", "Documento oficial")),
        url=str(source.get("url", "")),
        locator=str(source.get("locators", "")).strip() or None,
        locator_verified=precise,
        validity=str(source.get("validity", "Vigencia pendiente de verificación")),
    )


def build_daily_mission(
    *,
    opec_number: object,
    available_minutes: int,
    function_evidence: Iterable[FunctionEvidence] = (),
    exam_date: date | None = None,
    today: date | None = None,
    target_score: float | None = None,
) -> DailyStudyMission | None:
    """Build one concrete mission, or ``None`` when no matrix is available."""
    blueprint = load_preparation_blueprint(opec_number)
    functions = list(blueprint.get("functions", []) or [])
    if not functions:
        return None

    evidence_by_number = {
        int(item.function_number): item for item in function_evidence
    }
    ranked = []
    for function in functions:
        number = int(function.get("number", 0) or 0)
        evidence = evidence_by_number.get(number, FunctionEvidence(number))
        ranked.append(
            (
                -_function_priority(
                    evidence,
                    int(function.get("functional_question_target", 1) or 1),
                ),
                number,
                function,
                evidence,
            )
        )
    _, function_number, function, evidence = sorted(ranked)[0]

    timed = build_timed_session(available_minutes)
    source_by_id = {
        str(item.get("id")): item for item in blueprint.get("sources", []) or []
    }
    source = _pick_source(function, source_by_id)
    knowledge = [str(item) for item in function.get("knowledge", []) if str(item).strip()]
    topic = knowledge[0] if knowledge else str(function.get("short_name", "Función prioritaria"))
    locator_instruction = (
        f"en {source.locator}"
        if source and source.locator_verified
        else "solo en el localizador que la biblioteca confirme antes de estudiar"
    )
    activities = (
        StudyActivitySpec(
            "active_recall",
            timed.review_minutes,
            f"Recupera de memoria la regla central de {topic} y anota una duda.",
        ),
        StudyActivitySpec(
            "directed_reading",
            timed.learning_minutes,
            (
                f"Lee {source.name} {locator_instruction}."
                if source
                else "No leas una norma al azar: espera una fuente oficial vinculada."
            ),
        ),
        StudyActivitySpec(
            "pjs_practice",
            timed.practice_minutes,
            f"Resuelve hasta {timed.question_goal} preguntas nuevas vinculadas con F{function_number}.",
        ),
        StudyActivitySpec(
            "error_review",
            timed.closing_minutes,
            "Registra la regla, la excepción y el error que debes volver a demostrar con otra pregunta.",
        ),
    )
    remaining = days_until_exam(exam_date, today=today)
    configured_target = (
        float(target_score)
        if target_score is not None
        else float(blueprint.get("target_score", 85) or 85)
    )
    configured_target = _clamp(configured_target, 0.0, 100.0)
    reason_parts = [
        f"dominio observado {evidence.mastery_score:.1f}%",
        f"{evidence.attempts} respuestas",
        f"{evidence.trusted_question_count} preguntas confiables disponibles",
    ]
    if evidence.due_error_count:
        reason_parts.append(f"{evidence.due_error_count} errores vencidos")
    return DailyStudyMission(
        opec_number=str(opec_number),
        function_number=function_number,
        function_name=str(function.get("short_name", f"Función {function_number}")),
        topic=topic,
        total_minutes=timed.total_minutes,
        question_goal=timed.question_goal,
        target_score=configured_target,
        target_status="objetivo interno de precisión, no corte oficial",
        reason="Se prioriza por " + ", ".join(reason_parts) + ".",
        source=source,
        activities=activities,
        question_ids=tuple(evidence.question_ids[: timed.question_goal]),
        days_remaining=remaining,
        phase=preparation_phase(remaining),
    )
