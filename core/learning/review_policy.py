"""Versioned, provider-free spaced-review policy.

This policy is an internal learning aid, not an official CNSC scoring rule.
Confidence changes review priority only; it never changes whether an answer is
correct or the score awarded for it.
"""

from __future__ import annotations

from dataclasses import dataclass


POLICY_VERSION = "review-internal-v1"

_CONFIDENCE_ALIASES = {
    "guess": "low",
    "unsure": "medium",
    "confident": "high",
    "low": "low",
    "medium": "medium",
    "high": "high",
}

_FIRST_CORRECT_DAYS = {"low": 1.0, "medium": 2.0, "high": 4.0}
_CORRECT_GROWTH = {"low": 1.2, "medium": 1.8, "high": 2.6}

# A confident error is evidence of a possible misconception, so it is due no
# later than an uncertain error.  This ordering is deliberately the reverse of
# the interval used for correct answers.
_INCORRECT_DAYS = {"low": 1.0, "medium": 0.5, "high": 0.25}
_PARTIAL_DAYS = {"low": 1.0, "medium": 0.75, "high": 0.5}


@dataclass(frozen=True)
class ReviewDecision:
    interval_days: float
    normalized_confidence: str
    policy_version: str = POLICY_VERSION


def normalize_confidence(confidence: str | None) -> str | None:
    """Return the canonical confidence label, preserving missing telemetry."""
    if confidence is None or not str(confidence).strip():
        return None
    try:
        return _CONFIDENCE_ALIASES[str(confidence).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Nivel de confianza no valido: {confidence}") from exc


def review_interval(
    *,
    result: str,
    confidence: str | None,
    previous_interval_days: float = 0.0,
    review_count: int = 0,
    ease_factor: float = 2.5,
) -> ReviewDecision:
    """Calculate the next interval without inferring missing confidence.

    Missing confidence is treated as ``medium`` only for scheduling continuity;
    callers must continue storing it as unknown in the learning event.
    """
    outcome = str(result or "").strip().lower()
    if outcome not in {"correct", "partial", "incorrect"}:
        raise ValueError(f"Resultado no valido: {result}")
    normalized = normalize_confidence(confidence) or "medium"
    previous = max(0.0, float(previous_interval_days or 0.0))
    count = max(0, int(review_count or 0))
    ease = min(3.0, max(1.3, float(ease_factor or 2.5)))

    if outcome == "incorrect":
        interval = _INCORRECT_DAYS[normalized]
    elif outcome == "partial":
        interval = _PARTIAL_DAYS[normalized]
    elif count <= 0 or previous <= 0:
        interval = _FIRST_CORRECT_DAYS[normalized]
    else:
        interval = max(1.0, previous * _CORRECT_GROWTH[normalized] * (ease / 2.5))

    return ReviewDecision(
        interval_days=round(min(max(interval, 0.25), 180.0), 4),
        normalized_confidence=normalized,
    )
