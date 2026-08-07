"""Pesos explícitos y centralizados del motor adaptativo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PriorityWeights:
    mastery_gap: float = 0.35
    overdue_review: float = 0.20
    recent_errors: float = 0.20
    low_confidence: float = 0.10
    importance: float = 0.10
    study_staleness: float = 0.05


PRIORITY_WEIGHTS = PriorityWeights()
MASTERY_LEARNING_RATE = 0.20
RESULT_SCORES = {"correct": 1.0, "partial": 0.6, "incorrect": 0.0}
CONFIDENCE_STRENGTH = {"low": 0.80, "medium": 1.00, "high": 1.10}
