from dataclasses import dataclass
from datetime import datetime
import math
import random
from typing import List, Mapping, Optional, Tuple

from db.models import Question, QuestionPerformance, Skill


SkillKey = Tuple[str, str, str]


@dataclass(frozen=True)
class DailyRecommendation:
    question: Question
    score: float
    reasons: tuple[str, ...]


def calculate_mastery_update(is_correct: bool, current_mastery: float) -> float:
    """Actualiza el dominio de una habilidad en una escala de 0 a 100."""
    if is_correct:
        delta = 5.0 * ((100 - current_mastery) / 100.0)
        return min(100.0, current_mastery + delta)

    return max(0.0, current_mastery - 10.0)


def update_priority(current_priority: float, is_correct: bool) -> float:
    if not is_correct:
        return current_priority + 2.0
    return max(1.0, current_priority - 0.5)


def _question_score(
    question: Question,
    skill: Optional[Skill],
    performance: Optional[QuestionPerformance],
    now: datetime,
) -> tuple[float, tuple[str, ...]]:
    """Calcula el valor pedagógico de practicar una pregunta hoy."""
    mastery = float(getattr(skill, "mastery_score", 0.0) or 0.0)
    mastery_gap = 1.0 - min(max(mastery, 0.0), 100.0) / 100.0

    hits = int(getattr(performance, "hits", 0) or 0)
    misses = int(getattr(performance, "misses", 0) or 0)
    attempts = hits + misses
    # Suavizado bayesiano: evita extremos con muy pocos intentos.
    error_risk = (misses + 1.0) / (attempts + 2.0)

    last_attempt = getattr(performance, "last_attempt", None)
    if last_attempt:
        comparison_now = now
        if last_attempt.tzinfo and not comparison_now.tzinfo:
            comparison_now = comparison_now.replace(tzinfo=last_attempt.tzinfo)
        elif comparison_now.tzinfo and not last_attempt.tzinfo:
            comparison_now = comparison_now.replace(tzinfo=None)
        days_since = max((comparison_now - last_attempt).total_seconds() / 86400.0, 0.0)
        overdue = min(days_since / 14.0, 1.0)
    else:
        days_since = None
        overdue = 1.0

    priority_weight = float(getattr(skill, "priority_weight", 1.0) or 1.0)
    priority = min(max(priority_weight - 1.0, 0.0) / 6.0, 1.0)
    unseen_bonus = 1.0 if attempts == 0 else 0.0
    challenge = min(max((int(getattr(question, "difficulty", 2) or 2) - 1) / 2.0, 0.0), 1.0)

    score = (
        0.35 * mastery_gap
        + 0.25 * error_risk
        + 0.20 * overdue
        + 0.10 * priority
        + 0.08 * unseen_bonus
        + 0.02 * challenge
    )

    reasons = []
    if mastery < 50:
        reasons.append("dominio bajo")
    if attempts and error_risk >= 0.5:
        reasons.append("errores recurrentes")
    if attempts == 0:
        reasons.append("pregunta nueva")
    elif days_since is not None and days_since >= 7:
        reasons.append("repaso pendiente")
    if priority_weight >= 3:
        reasons.append("tema prioritario")
    if not reasons:
        reasons.append("mantenimiento")

    return score, tuple(reasons)


def build_daily_plan(
    all_questions: List[Question],
    skills_map: Mapping[SkillKey, Skill],
    performance_map: Mapping[str, QuestionPerformance],
    n: int = 20,
    now: Optional[datetime] = None,
) -> List[DailyRecommendation]:
    """Construye un plan diario priorizado, variado y reproducible."""
    if n <= 0 or not all_questions:
        return []

    now = now or datetime.utcnow()
    ranked = []
    for question in all_questions:
        key = (question.track, question.competency, question.topic)
        score, reasons = _question_score(
            question,
            skills_map.get(key),
            performance_map.get(question.question_id),
            now,
        )
        ranked.append(DailyRecommendation(question, score, reasons))

    ranked.sort(key=lambda item: (-item.score, str(item.question.question_id)))

    # Impide que un solo tema monopolice la sesión, sin descartar candidatos.
    per_topic_limit = max(2, math.ceil(min(n, len(ranked)) * 0.20))
    selected = []
    deferred = []
    topic_counts = {}
    for item in ranked:
        topic = item.question.topic or "Sin tema"
        if topic_counts.get(topic, 0) < per_topic_limit and len(selected) < n:
            selected.append(item)
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        else:
            deferred.append(item)

    if len(selected) < n:
        deferred_by_topic = {}
        topic_order = []
        for item in deferred:
            topic = item.question.topic or "Sin tema"
            if topic not in deferred_by_topic:
                deferred_by_topic[topic] = []
                topic_order.append(topic)
            deferred_by_topic[topic].append(item)

        while len(selected) < n and any(deferred_by_topic.values()):
            for topic in topic_order:
                if deferred_by_topic[topic] and len(selected) < n:
                    selected.append(deferred_by_topic[topic].pop(0))

    return selected[:n]


def build_remaining_daily_plan(
    all_questions: List[Question],
    skills_map: Mapping[SkillKey, Skill],
    performance_map: Mapping[str, QuestionPerformance],
    completed_question_ids: set[str],
    daily_goal: int = 20,
    now: Optional[datetime] = None,
) -> List[DailyRecommendation]:
    """Devuelve sólo las preguntas que faltan para completar la meta diaria."""
    completed_count = min(len(completed_question_ids), max(daily_goal, 0))
    remaining_count = max(daily_goal - completed_count, 0)
    if remaining_count == 0:
        return []

    eligible_questions = [
        question
        for question in all_questions
        if question.question_id not in completed_question_ids
    ]
    return build_daily_plan(
        eligible_questions,
        skills_map,
        performance_map,
        n=remaining_count,
        now=now,
    )

def select_daily_questions(
    all_questions: List[Question],
    skills_map: Mapping[SkillKey, Skill],
    performance_map: Mapping[str, QuestionPerformance],
    n: int = 20,
    now: Optional[datetime] = None,
) -> List[Question]:
    return [item.question for item in build_daily_plan(all_questions, skills_map, performance_map, n, now)]


def select_questions_for_simulation(
    all_questions: List[Question],
    skills_map: dict,
    n: int = 20,
) -> List[Question]:
    """Selector adaptativo general usado por los simulacros configurables."""
    weak_questions = []
    medium_questions = []
    strong_questions = []

    for question in all_questions:
        key = (question.track, question.competency, question.topic)
        skill = skills_map.get(key)
        mastery = skill.mastery_score if skill else 0.0

        if mastery < 50:
            weak_questions.append(question)
        elif mastery < 80:
            medium_questions.append(question)
        else:
            strong_questions.append(question)

    n_weak = int(n * 0.60)
    n_medium = int(n * 0.25)

    def sample_safe(pool, count):
        return random.sample(pool, min(len(pool), count))

    selected = sample_safe(weak_questions, n_weak)
    remaining_weak_slots = n_weak - len(selected)
    selected.extend(sample_safe(medium_questions, n_medium + remaining_weak_slots))
    selected.extend(sample_safe(strong_questions, n - len(selected)))

    if len(selected) < n:
        remaining = [question for question in all_questions if question not in selected]
        selected.extend(sample_safe(remaining, n - len(selected)))

    random.shuffle(selected)
    return selected