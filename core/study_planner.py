from dataclasses import dataclass
from datetime import date
import math
from typing import Optional


@dataclass(frozen=True)
class TimedStudySession:
    total_minutes: int
    review_minutes: int
    learning_minutes: int
    practice_minutes: int
    closing_minutes: int
    question_goal: int


def build_timed_session(total_minutes: int) -> TimedStudySession:
    """Distribuye una sesión entre recuperación, aprendizaje, práctica y cierre."""
    minutes = min(max(int(total_minutes or 30), 15), 180)
    review = max(3, round(minutes * 0.17))
    learning = max(5, round(minutes * 0.40))
    practice = max(5, round(minutes * 0.33))
    closing = minutes - review - learning - practice
    if closing < 2:
        learning -= 2 - closing
        closing = 2
    question_goal = max(3, min(30, math.ceil(practice / 2)))
    return TimedStudySession(
        total_minutes=minutes,
        review_minutes=review,
        learning_minutes=learning,
        practice_minutes=practice,
        closing_minutes=closing,
        question_goal=question_goal,
    )


def days_until_exam(exam_date: Optional[date], today: Optional[date] = None) -> Optional[int]:
    if exam_date is None:
        return None
    today = today or date.today()
    return max((exam_date - today).days, 0)


def preparation_phase(days_remaining: Optional[int]) -> str:
    if days_remaining is None:
        return "Fecha pendiente"
    if days_remaining <= 14:
        return "Repaso final"
    if days_remaining <= 42:
        return "Simulacros y corrección"
    if days_remaining <= 84:
        return "Integración y casos"
    return "Cobertura del temario"