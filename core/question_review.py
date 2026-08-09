"""Safe review transitions for questions generated as study candidates."""

from __future__ import annotations

from datetime import date
from typing import Optional


REINFORCEMENT_REVIEW = "reinforcement_candidate"
PROGRESSIVE_OPEC_REVIEW = "progressive_opec_local"
MANUAL_QUESTION_REVIEW = "manual_question_review"
QUALITY_ALL = "Todas"
QUALITY_VERIFIED = "Solo verificadas ✅"
QUALITY_PENDING = "Pendientes generales ⏳"
QUALITY_REINFORCEMENTS = "Refuerzos por revisar 🧪"


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


def matches_quality_filter(question, selected: str) -> bool:
    if selected == QUALITY_VERIFIED:
        return bool(getattr(question, "is_verified", False))
    if selected == QUALITY_PENDING:
        return not bool(getattr(question, "is_verified", False))
    if selected == QUALITY_REINFORCEMENTS:
        return is_reinforcement_candidate(question)
    return True
