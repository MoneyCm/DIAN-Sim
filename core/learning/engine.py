"""Funciones puras del motor adaptativo.

Prioridad = 0.35 brecha de dominio + 0.20 revisión vencida
          + 0.20 tasa de error reciente + 0.10 baja confianza
          + 0.10 importancia + 0.05 tiempo sin estudiar.

Cada factor se normaliza entre 0 y 1. El dominio usa una media móvil:
    nuevo = actual + (0.20 * fuerza_confianza) * (resultado - actual)
donde resultado vale 1.0, 0.6 o 0.0. La fórmula es determinística y no usa IA.
"""

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Iterable, Mapping, Optional

from core.learning.config import (
    CONFIDENCE_STRENGTH,
    MASTERY_LEARNING_RATE,
    PRIORITY_WEIGHTS,
    RESULT_SCORES,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def topic_id_for(track: str, competency: str, topic: str) -> str:
    raw = "|".join((track or "General", competency or "General", topic or "Sin tema"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def calculate_mastery(current_mastery: float, result: str, confidence: str) -> float:
    if result not in RESULT_SCORES:
        raise ValueError(f"Resultado no válido: {result}")
    if confidence not in CONFIDENCE_STRENGTH:
        raise ValueError(f"Seguridad no válida: {confidence}")
    current = min(max(float(current_mastery), 0.0), 100.0) / 100.0
    target = RESULT_SCORES[result]
    alpha = MASTERY_LEARNING_RATE * CONFIDENCE_STRENGTH[confidence]
    return round(min(max(current + alpha * (target - current), 0.0), 1.0) * 100.0, 2)


def schedule_next_review(
    result: str,
    confidence: str,
    mastery_score: float,
    *,
    now: Optional[datetime] = None,
) -> datetime:
    if result not in RESULT_SCORES or confidence not in CONFIDENCE_STRENGTH:
        raise ValueError("Resultado o seguridad no válidos")
    now = now or utc_now()
    base_days = {
        "correct": {"low": 2.0, "medium": 4.0, "high": 7.0},
        "partial": {"low": 0.5, "medium": 1.0, "high": 2.0},
        "incorrect": {"low": 0.25, "medium": 0.5, "high": 1.0},
    }[result][confidence]
    mastery_factor = 0.75 + min(max(mastery_score, 0.0), 100.0) / 200.0
    return now + timedelta(days=max(0.25, base_days * mastery_factor))


def calculate_topic_priority(
    *,
    mastery_score: float,
    next_review_at: Optional[datetime],
    recent_error_rate: float,
    low_confidence_rate: float,
    importance: float,
    last_studied_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> float:
    now = now or utc_now()
    mastery_gap = 1.0 - min(max(mastery_score, 0.0), 100.0) / 100.0
    overdue = 1.0 if next_review_at is None or next_review_at <= now else 0.0
    errors = min(max(recent_error_rate, 0.0), 1.0)
    low_confidence = min(max(low_confidence_rate, 0.0), 1.0)
    importance_norm = min(max(importance, 0.0), 2.0) / 2.0
    if last_studied_at is None:
        staleness = 1.0
    else:
        staleness = min(max((now - last_studied_at).total_seconds(), 0.0) / (30 * 86400), 1.0)
    weights = PRIORITY_WEIGHTS
    score = (
        weights.mastery_gap * mastery_gap
        + weights.overdue_review * overdue
        + weights.recent_errors * errors
        + weights.low_confidence * low_confidence
        + weights.importance * importance_norm
        + weights.study_staleness * staleness
    )
    return round(score, 6)


def difficulty_for_mastery(mastery_score: float, attempts: int = 0) -> int:
    """Unlock difficulty gradually; new topics always begin at the basic level."""
    mastery = min(max(float(mastery_score or 0.0), 0.0), 100.0)
    if int(attempts or 0) < 3 or mastery < 40.0:
        return 1
    if mastery < 75.0:
        return 2
    return 3


def select_next_question(
    questions: Iterable,
    topic_priorities: Mapping[str, float],
    *,
    excluded_question_ids: Optional[set[str]] = None,
    topic_mastery_scores: Optional[Mapping[str, float]] = None,
    topic_attempt_counts: Optional[Mapping[str, int]] = None,
):
    """Selecciona de forma reproducible la mejor pregunta disponible."""
    excluded = excluded_question_ids or set()
    candidates = [q for q in questions if str(q.question_id) not in excluded]
    if not candidates:
        return None

    def rank(question):
        topic_id = topic_id_for(question.track, question.competency, question.topic)
        mastery = (topic_mastery_scores or {}).get(topic_id, 0.0)
        attempts = (topic_attempt_counts or {}).get(topic_id, 0)
        target_difficulty = difficulty_for_mastery(mastery, attempts)
        question_difficulty = min(max(int(question.difficulty or 2), 1), 3)
        return (
            abs(question_difficulty - target_difficulty),
            -topic_priorities.get(topic_id, 0.5),
            str(question.question_id),
        )

    return sorted(candidates, key=rank)[0]
