from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from core.learning.review_policy import review_interval


CONFIDENCE_EASE_DELTA = {
    "guess": -0.15,
    "unsure": 0.0,
    "confident": 0.1,
}

@dataclass(frozen=True)
class ReviewSchedule:
    interval_days: float
    next_review: datetime
    ease_factor: float
    review_count: int
    lapse_count: int


def schedule_review(
    performance,
    is_correct: bool,
    confidence: str = "unsure",
    error_type: Optional[str] = None,
    now: Optional[datetime] = None,
) -> ReviewSchedule:
    """Actualiza una ficha de rendimiento con su siguiente fecha de repaso."""
    if confidence not in CONFIDENCE_EASE_DELTA:
        raise ValueError(f"Nivel de confianza no válido: {confidence}")

    now = now or datetime.now()
    previous_interval = float(getattr(performance, "review_interval_days", 0.0) or 0.0)
    previous_reviews = int(getattr(performance, "review_count", 0) or 0)
    lapse_count = int(getattr(performance, "lapse_count", 0) or 0)
    ease_factor = float(getattr(performance, "ease_factor", 2.5) or 2.5)

    if is_correct:
        decision = review_interval(
            result="correct",
            confidence=confidence,
            previous_interval_days=previous_interval,
            review_count=previous_reviews,
            ease_factor=ease_factor,
        )
        interval = decision.interval_days
        ease_factor = min(3.0, max(1.3, ease_factor + CONFIDENCE_EASE_DELTA[confidence]))
        stored_error_type = None
    else:
        decision = review_interval(result="incorrect", confidence=confidence)
        interval = decision.interval_days
        ease_factor = max(1.3, ease_factor - 0.2)
        lapse_count += 1
        stored_error_type = error_type or "sin_clasificar"

    review_count = previous_reviews + 1
    next_review = now + timedelta(days=interval)

    performance.review_interval_days = interval
    performance.ease_factor = ease_factor
    performance.review_count = review_count
    performance.lapse_count = lapse_count
    performance.last_confidence = confidence
    performance.last_error_type = stored_error_type
    performance.last_reviewed_at = now
    performance.next_review = next_review
    # A long scheduling interval alone is not proof of transfer or retention.
    # Canonical mastery is evaluated separately from review timing.
    if not is_correct:
        performance.is_mastered = False

    return ReviewSchedule(
        interval_days=interval,
        next_review=next_review,
        ease_factor=ease_factor,
        review_count=review_count,
        lapse_count=lapse_count,
    )


def is_review_due(performance, now: Optional[datetime] = None) -> bool:
    """Indica si una pregunta debe aparecer en la cola de repaso."""
    now = now or datetime.now()
    next_review = getattr(performance, "next_review", None)
    if next_review is None:
        return bool((getattr(performance, "misses", 0) or 0) > 0)
    if next_review.tzinfo and not now.tzinfo:
        now = now.replace(tzinfo=next_review.tzinfo)
    elif now.tzinfo and not next_review.tzinfo:
        now = now.replace(tzinfo=None)
    return next_review <= now
