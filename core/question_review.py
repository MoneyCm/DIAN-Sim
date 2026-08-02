"""Safe review transitions for questions generated as study candidates."""

from __future__ import annotations

from typing import Optional


REINFORCEMENT_REVIEW = "reinforcement_candidate"


def is_reinforcement_candidate(question) -> bool:
    report = getattr(question, "quality_report", None)
    return (
        isinstance(report, dict)
        and report.get("review") == REINFORCEMENT_REVIEW
        and report.get("status") == "PENDING_REVIEW"
        and not bool(getattr(question, "is_verified", False))
    )


def candidate_validation_error(question) -> Optional[str]:
    """Return the first reason a candidate cannot be manually approved."""
    if not is_reinforcement_candidate(question):
        return "La pregunta no es un refuerzo pendiente de revisión."
    if not str(getattr(question, "source_refs", "") or "").strip():
        return "Falta una fuente normativa verificable."
    if not str(getattr(question, "stem", "") or "").strip():
        return "Falta el enunciado."
    options = getattr(question, "options_json", None)
    if not isinstance(options, dict) or tuple(options.keys()) != ("A", "B", "C"):
        return "Debe tener exactamente tres opciones: A, B y C."
    if getattr(question, "correct_key", None) not in options:
        return "La respuesta correcta no corresponde a una opción válida."
    if not str(getattr(question, "rationale", "") or "").strip():
        return "Falta la justificación de la respuesta."
    return None


def approve_candidate(question, reviewer: str) -> None:
    """Promote a reviewed candidate to source-grounded active practice."""
    error = candidate_validation_error(question)
    if error:
        raise ValueError(error)
    report = dict(question.quality_report or {})
    report.update(
        status="APPROVED",
        review="human_source_grounded",
        origin=REINFORCEMENT_REVIEW,
        reviewed_by=reviewer,
    )
    question.quality_report = report
    question.is_verified = True


def reject_candidate(question, reviewer: str, reason: str = "") -> None:
    if not is_reinforcement_candidate(question):
        raise ValueError("La pregunta no es un refuerzo pendiente de revisión.")
    report = dict(question.quality_report or {})
    report.update(
        status="REJECTED",
        review="human_rejected",
        origin=REINFORCEMENT_REVIEW,
        reviewed_by=reviewer,
        rejection_reason=reason.strip(),
    )
    question.quality_report = report
    question.is_verified = False


def record_ai_audit(question, audit_report: dict) -> None:
    """Store an AI opinion without turning it into a trust decision."""
    current = getattr(question, "quality_report", None)
    if is_reinforcement_candidate(question):
        report = dict(current)
        report["ai_audit"] = audit_report
        question.quality_report = report
    else:
        question.quality_report = {
            "status": "PENDING_HUMAN_REVIEW",
            "review": "ai_audit_only",
            "ai_audit": audit_report,
        }
    question.is_verified = False
