"""Safe review transitions for questions generated as study candidates."""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.source_evidence import precise_source_verification_error
from core.question_quality import audit_question_structure


REINFORCEMENT_REVIEW = "reinforcement_candidate"
PROGRESSIVE_OPEC_REVIEW = "progressive_opec_local"
MANUAL_QUESTION_REVIEW = "manual_question_review"
QUALITY_ALL = "Todas"
QUALITY_VERIFIED = "Solo verificadas ✅"
QUALITY_PENDING = "Pendientes generales ⏳"
QUALITY_REINFORCEMENTS = "Refuerzos por revisar 🧪"
EDITORIAL_CONTRACT_VERSION = "pjs-editorial-v2"
COGNITIVE_LEVELS = frozenset({
    "recognition",
    "application",
    "analysis",
    "judgment",
    "transfer",
})


def editorial_metadata_error(question) -> Optional[str]:
    report = getattr(question, "quality_report", None)
    metadata = report.get("editorial_metadata") if isinstance(report, dict) else None
    if not isinstance(metadata, dict):
        return "Falta la ficha editorial individual de la pregunta."
    if not str(metadata.get("subtopic", "")).strip():
        return "Falta registrar el subtema."
    if str(metadata.get("cognitive_level", "")).strip() not in COGNITIVE_LEVELS:
        return "Falta un nivel cognitivo válido."
    try:
        function_number = int(metadata.get("function_number"))
    except (TypeError, ValueError):
        return "Falta vincular la función de la OPEC."
    if function_number < 1:
        return "La función vinculada no es válida."
    try:
        difficulty = int(report.get("editorial_difficulty_1_10"))
    except (TypeError, ValueError):
        return "Falta la dificultad editorial de 1 a 10."
    if not 1 <= difficulty <= 10:
        return "La dificultad editorial debe estar entre 1 y 10."

    question_type = str(getattr(question, "question_type", "") or "").upper()
    track = str(getattr(question, "track", "") or "").upper()
    if question_type == "LIKERT" or track in {"COMPORTAMENTAL", "INTEGRIDAD"}:
        return None
    options = getattr(question, "options_json", None) or {}
    correct = getattr(question, "correct_key", None)
    explanations = metadata.get("distractor_explanations")
    if not isinstance(explanations, dict):
        return "Falta explicar por qué los distractores no son la mejor respuesta."
    for key in options:
        if key == correct:
            continue
        if len(str(explanations.get(key, "")).strip()) < 10:
            return f"Falta explicar el distractor {key}."
    return None


def record_editorial_verification(
    question,
    *,
    source_status: str,
    source_url: str,
    source_locator: str,
    supporting_excerpt: str,
    verified_on: str,
    verified_by: str,
    subtopic: str,
    cognitive_level: str,
    function_number: int,
    editorial_difficulty: int,
    distractor_explanations: dict | None = None,
) -> None:
    """Persist the human normative/editorial evidence needed before approval."""

    try:
        date.fromisoformat(str(verified_on))
    except (TypeError, ValueError) as exc:
        raise ValueError("La fecha de verificación debe usar formato AAAA-MM-DD.") from exc
    if cognitive_level not in COGNITIVE_LEVELS:
        raise ValueError("El nivel cognitivo no es válido.")
    if not 1 <= int(editorial_difficulty) <= 10:
        raise ValueError("La dificultad editorial debe estar entre 1 y 10.")
    if int(function_number) < 1:
        raise ValueError("La función de la OPEC no es válida.")

    original_report = getattr(question, "quality_report", None)
    report = dict(original_report or {})
    report["source_verification"] = {
        "status": str(source_status or "").strip(),
        "url": str(source_url or "").strip(),
        "locator": str(source_locator or "").strip(),
        "supporting_excerpt": str(supporting_excerpt or "").strip(),
        "verified_on": str(verified_on),
        "verified_by": str(verified_by or "").strip(),
    }
    report["editorial_metadata"] = {
        "contract_version": EDITORIAL_CONTRACT_VERSION,
        "subtopic": str(subtopic or "").strip(),
        "cognitive_level": cognitive_level,
        "function_number": int(function_number),
        "distractor_explanations": {
            str(key): str(value or "").strip()
            for key, value in (distractor_explanations or {}).items()
        },
    }
    report["editorial_difficulty_1_10"] = int(editorial_difficulty)
    question.quality_report = report
    error = precise_source_verification_error(question) or editorial_metadata_error(question)
    if error:
        question.quality_report = original_report
        raise ValueError(error)


def is_reinforcement_candidate(question) -> bool:
    report = getattr(question, "quality_report", None)
    return (
        isinstance(report, dict)
        and report.get("review") == REINFORCEMENT_REVIEW
        and report.get("status") == "PENDING_REVIEW"
        and not bool(getattr(question, "is_verified", False))
    )


def is_pending_review_candidate(question) -> bool:
    """Return whether an unverified question is eligible for a human decision."""
    if bool(getattr(question, "is_verified", False)):
        return False
    report = getattr(question, "quality_report", None)
    return not (isinstance(report, dict) and report.get("status") == "REJECTED")


def is_review_queue_item(question) -> bool:
    """Return whether a question belongs to the explicit human-review queue."""
    report = getattr(question, "quality_report", None)
    if isinstance(report, dict) and report.get("origin") in {
        REINFORCEMENT_REVIEW,
        PROGRESSIVE_OPEC_REVIEW,
        MANUAL_QUESTION_REVIEW,
    }:
        return True
    # Older progressive banks did not persist their origin. If they remain
    # unverified, have a declared source and were not rejected, they still
    # require a review decision instead of disappearing from the queue.
    return is_pending_review_candidate(question) and bool(
        str(getattr(question, "source_refs", "") or "").strip()
    )


def review_queue_summary(questions) -> dict:
    """Summarize the auditable candidates without treating old bank items as queue work."""
    items = [question for question in questions if is_review_queue_item(question)]
    pending = [question for question in items if is_pending_review_candidate(question)]
    statuses = [
        (getattr(question, "quality_report", None) or {}).get("status")
        for question in items
    ]
    return {
        "total": len(items),
        "pending": len(pending),
        "approved": statuses.count("APPROVED"),
        "rejected": statuses.count("REJECTED"),
        "next_question": min(
            pending, key=lambda item: str(getattr(item, "question_id", "")), default=None
        ),
    }


def candidate_validation_error(question) -> Optional[str]:
    """Return the first reason a candidate cannot be manually approved."""
    if not is_pending_review_candidate(question):
        return "La pregunta no está pendiente de revisión."
    if not str(getattr(question, "source_refs", "") or "").strip():
        return "Falta una fuente normativa verificable."
    if not str(getattr(question, "stem", "") or "").strip():
        return "Falta el enunciado."
    options = getattr(question, "options_json", None)
    question_type = str(getattr(question, "question_type", "") or "").upper()
    track = str(getattr(question, "track", "") or "").upper()
    is_likert = question_type == "LIKERT" or track in {"COMPORTAMENTAL", "INTEGRIDAD"}
    if is_likert:
        if not isinstance(options, dict) or len(options) != 4:
            return "La afirmación Likert debe tener exactamente cuatro opciones de respuesta."
        if getattr(question, "correct_key", None) not in (None, ""):
            return "Una afirmación de autorreporte Likert no debe tener respuesta correcta."
    else:
        if not isinstance(options, dict) or tuple(options.keys()) != ("A", "B", "C"):
            return "Debe tener exactamente tres opciones: A, B y C."
        if getattr(question, "correct_key", None) not in options:
            return "La respuesta correcta no corresponde a una opción válida."
    if not str(getattr(question, "rationale", "") or "").strip():
        return "Falta la justificación de la respuesta."
    source_error = precise_source_verification_error(question)
    if source_error:
        return source_error
    structural = audit_question_structure(question)
    structural_errors = [
        finding["message"]
        for finding in structural["findings"]
        if finding["severity"] == "error"
    ]
    if structural_errors:
        return structural_errors[0]
    metadata_error = editorial_metadata_error(question)
    if metadata_error:
        return metadata_error
    return None


def approve_candidate(question, reviewer: str) -> None:
    """Promote a reviewed candidate to source-grounded active practice."""
    error = candidate_validation_error(question)
    if error:
        raise ValueError(error)
    report = dict(question.quality_report or {})
    origin = report.get("origin") or (
        REINFORCEMENT_REVIEW if is_reinforcement_candidate(question) else MANUAL_QUESTION_REVIEW
    )
    report.update(
        status="APPROVED",
        review="human_source_grounded",
        origin=origin,
        reviewed_by=reviewer,
        reviewed_at=date.today().isoformat(),
    )
    question.quality_report = report
    question.is_verified = True


def reject_candidate(question, reviewer: str, reason: str = "") -> None:
    if not is_pending_review_candidate(question):
        raise ValueError("La pregunta no está pendiente de revisión.")
    report = dict(question.quality_report or {})
    origin = report.get("origin") or (
        REINFORCEMENT_REVIEW if is_reinforcement_candidate(question) else MANUAL_QUESTION_REVIEW
    )
    report.update(
        status="REJECTED",
        review="human_rejected",
        origin=origin,
        reviewed_by=reviewer,
        reviewed_at=date.today().isoformat(),
        rejection_reason=reason.strip(),
    )
    question.quality_report = report
    question.is_verified = False


def record_ai_audit(question, audit_report: dict) -> None:
    """Store an AI opinion without turning it into a trust decision."""
    report = dict(getattr(question, "quality_report", None) or {})
    report.setdefault("origin", MANUAL_QUESTION_REVIEW)
    report.setdefault("status", "PENDING_HUMAN_REVIEW")
    report.setdefault("review", "ai_audit_only")
    report["ai_audit"] = audit_report
    question.quality_report = report
    question.is_verified = False


def has_ai_audit(question) -> bool:
    """Return whether an AI opinion has already been stored for a candidate.

    AI auditing does not approve a candidate, so it remains in the human queue.
    This marker lets an interrupted batch resume without using tokens twice.
    """
    report = getattr(question, "quality_report", None)
    return isinstance(report, dict) and isinstance(report.get("ai_audit"), dict)


def automatic_rejection_reason(question) -> Optional[str]:
    """Return a conservative reason for automatically discarding a candidate.

    This only retires content that has no traceable source or that an AI audit
    explicitly rejects.  An audit *error* alone is not evidence against a
    question, so it never triggers a rejection without an untraceable source.
    """
    report = getattr(question, "quality_report", None)
    report = report if isinstance(report, dict) else {}
    audit = report.get("ai_audit")
    status = str(audit.get("status", "")).strip().upper() if isinstance(audit, dict) else ""
    source = str(getattr(question, "source_refs", "") or "").strip().lower()
    generated_source = (
        not source
        or "batch gen" in source
        or "banco base provisional" in source
        or "guía oficial pendiente" in source
        or "guia oficial pendiente" in source
        or "inyección especial" in source
        or "inyeccion especial" in source
        or "antigravity" in source
        or source.startswith(("mistral -", "openai -", "gemini -"))
    )

    if status == "REJECTED":
        return "Dictamen IA de rechazo; requiere reescritura o nueva fuente oficial."
    if generated_source:
        return "Fuente generada o provisional, sin trazabilidad oficial verificable."
    return None


def matches_quality_filter(question, selected: str) -> bool:
    if selected == QUALITY_VERIFIED:
        return bool(getattr(question, "is_verified", False))
    if selected == QUALITY_PENDING:
        return not bool(getattr(question, "is_verified", False))
    if selected == QUALITY_REINFORCEMENTS:
        return is_reinforcement_candidate(question)
    return True
