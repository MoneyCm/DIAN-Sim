"""Provider-free rules for the intelligent error notebook."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable


ERROR_CATEGORIES = {
    "norm_unknown": "Desconocimiento de la norma",
    "concept_confusion": "Confusión entre conceptos",
    "interpretation": "Interpretación incorrecta",
    "missed_exception": "No identificar una excepción",
    "rushed_reading": "Lectura apresurada",
    "time_management": "Mala administración del tiempo",
    "unjustified_answer_change": "Cambio injustificado de respuesta",
    "confidence_miscalibration": "Exceso o falta de confianza",
    "attractive_distractor": "Distractor atractivo",
    "forgetting": "Olvido",
}

LEGACY_ERROR_ALIASES = {
    "desconocimiento": "norm_unknown",
    "unknown_rule": "norm_unknown",
    "confusion_conceptual": "concept_confusion",
    "mala_interpretacion": "interpretation",
    "misinterpretation": "interpretation",
    "lectura_incompleta": "rushed_reading",
    "apuro": "time_management",
    "application": "interpretation",
    "unjustified_change": "unjustified_answer_change",
    "distractor": "attractive_distractor",
    "overconfidence": "confidence_miscalibration",
    "sin_clasificar": "norm_unknown",
}


@dataclass(frozen=True)
class ErrorGuidance:
    category: str
    category_label: str
    user_reasoning: str | None
    why_it_failed: str
    rule_to_remember: str
    source_to_review: str | None
    micro_lesson: str


@dataclass(frozen=True)
class TransferEvidence:
    question_id: str
    revision_id: str | None
    correct: bool | None
    occurred_at: datetime
    is_novel: bool
    question_type: str = "SITUATIONAL"


@dataclass(frozen=True)
class ResolutionStatus:
    overcome: bool
    qualifying_transfer_count: int
    required_transfer_count: int
    earliest_valid_at: datetime
    reason: str


def normalize_error_category(value: str | None) -> str:
    raw = str(value or "").strip()
    canonical = LEGACY_ERROR_ALIASES.get(raw, raw)
    return canonical if canonical in ERROR_CATEGORIES else "norm_unknown"


def build_error_guidance(
    *,
    category: str | None,
    user_reasoning: str | None,
    rationale: str | None,
    source_reference: str | None,
) -> ErrorGuidance:
    canonical = normalize_error_category(category)
    rule = str(rationale or "").strip() or (
        "Reconstruye la regla desde una fuente oficial antes de volver a responder."
    )
    why = {
        "norm_unknown": "La decisión se tomó sin recuperar la regla jurídica aplicable.",
        "concept_confusion": "Se aplicó un concepto cercano, pero distinto del que resolvía el caso.",
        "interpretation": "Los hechos relevantes no se conectaron correctamente con la regla.",
        "missed_exception": "Se aplicó la regla general sin comprobar la excepción pertinente.",
        "rushed_reading": "Una condición del enunciado no fue incorporada al razonamiento.",
        "time_management": "La decisión se tomó con una distribución de tiempo ineficiente.",
        "unjustified_answer_change": "La respuesta inicial se cambió sin nueva evidencia del caso.",
        "confidence_miscalibration": "La seguridad declarada no coincidió con la precisión observada.",
        "attractive_distractor": "Una opción plausible desplazó a la alternativa mejor sustentada.",
        "forgetting": "La regla había sido estudiada, pero no pudo recuperarse a tiempo.",
    }[canonical]
    micro = (
        f"En una frase, explica cuándo aplica esta regla: {rule} "
        "Después identifica una excepción y resuelve una situación distinta."
    )
    return ErrorGuidance(
        category=canonical,
        category_label=ERROR_CATEGORIES[canonical],
        user_reasoning=str(user_reasoning).strip() if user_reasoning else None,
        why_it_failed=why,
        rule_to_remember=rule,
        source_to_review=str(source_reference).strip() if source_reference else None,
        micro_lesson=micro,
    )


def evaluate_error_resolution(
    *,
    original_question_id: str,
    opened_at: datetime,
    evidence: Iterable[TransferEvidence],
    minimum_delay_days: int = 3,
    required_novel_correct: int = 2,
) -> ResolutionStatus:
    """Require delayed success on different functional questions.

    Repeating the original item, answering immediately, or completing Likert
    self-report items cannot close a knowledge error.
    """
    delay_days = max(1, int(minimum_delay_days or 1))
    required = max(1, int(required_novel_correct or 1))
    earliest = opened_at + timedelta(days=delay_days)
    qualifying = [
        item
        for item in evidence
        if item.correct is True
        and item.is_novel
        and item.question_id != original_question_id
        and item.occurred_at >= earliest
        and str(item.question_type or "").upper() == "SITUATIONAL"
    ]
    # Distinct revisions/questions prevent one repeated item from counting
    # several times toward transfer.
    distinct = {
        (item.question_id, item.revision_id or item.question_id)
        for item in qualifying
    }
    count = len(distinct)
    overcome = count >= required
    return ResolutionStatus(
        overcome=overcome,
        qualifying_transfer_count=count,
        required_transfer_count=required,
        earliest_valid_at=earliest,
        reason=(
            "Debilidad superada con transferencia diferida en preguntas nuevas."
            if overcome
            else f"Faltan {required - count} demostración(es) diferida(s) en preguntas nuevas."
        ),
    )
