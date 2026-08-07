from dataclasses import dataclass
from datetime import datetime
import math
import random
from typing import List, Mapping, Optional, Tuple

from db.models import Question, QuestionPerformance, Skill
from core.exam_format import official_question_groups


SkillKey = Tuple[str, str, str]
DIAGNOSTIC_MIN_ATTEMPTS = 3


@dataclass(frozen=True)
class DailyRecommendation:
    question: Question
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class StudyPlanStage:
    code: str
    label: str
    diagnostic_share: float
    description: str


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

    now = now or datetime.now()
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


def _topic_key(question: Question) -> SkillKey:
    return (
        getattr(question, "track", None) or "Sin eje",
        getattr(question, "competency", None) or "Sin competencia",
        getattr(question, "topic", None) or "Sin tema",
    )


def topic_attempt_counts(
    questions: List[Question],
    performance_map: Mapping[str, QuestionPerformance],
) -> dict[SkillKey, int]:
    """Count all saved responses per topic, not just the current question."""
    counts: dict[SkillKey, int] = {}
    for question in questions:
        key = _topic_key(question)
        performance = performance_map.get(question.question_id)
        attempts = int(getattr(performance, "hits", 0) or 0) + int(
            getattr(performance, "misses", 0) or 0
        )
        counts[key] = counts.get(key, 0) + attempts
    return counts


def count_topics_requiring_diagnosis(
    questions: List[Question],
    performance_map: Mapping[str, QuestionPerformance],
    min_attempts: int = DIAGNOSTIC_MIN_ATTEMPTS,
) -> int:
    """Return topics without enough evidence to label mastery or weakness."""
    return sum(
        attempts < min_attempts
        for attempts in topic_attempt_counts(questions, performance_map).values()
    )


def build_study_plan_stage(
    questions: List[Question],
    performance_map: Mapping[str, QuestionPerformance],
    days_remaining: Optional[int] = None,
    min_attempts: int = DIAGNOSTIC_MIN_ATTEMPTS,
) -> StudyPlanStage:
    """Choose the daily-plan stage from evidence coverage and exam urgency."""
    total_topics = len(topic_attempt_counts(questions, performance_map))
    pending_topics = count_topics_requiring_diagnosis(
        questions, performance_map, min_attempts
    )
    pending_ratio = pending_topics / total_topics if total_topics else 0.0

    if days_remaining is not None and days_remaining <= 14:
        return StudyPlanStage(
            "final_review",
            "Repaso final",
            0.20 if pending_topics else 0.0,
            "Prioriza simulacros, errores y repasos; conserva una muestra mínima de temas sin medir.",
        )
    if days_remaining is not None and days_remaining <= 42:
        return StudyPlanStage(
            "exam_integration",
            "Simulacros y corrección",
            0.40 if pending_topics else 0.0,
            "Integra casos tipo examen sin abandonar los temas con evidencia insuficiente.",
        )
    if pending_ratio >= 0.50:
        return StudyPlanStage(
            "diagnostic",
            "Diagnóstico de cobertura",
            0.60,
            "Recoge evidencia de varios temas antes de interpretar debilidades.",
        )
    if pending_topics:
        return StudyPlanStage(
            "coverage",
            "Cobertura dirigida",
            0.40,
            "Completa los temas aún no medidos y refuerza los errores ya comprobados.",
        )
    return StudyPlanStage(
        "adaptive",
        "Adaptación consolidada",
        0.0,
        "Prioriza errores, repasos espaciados y mantenimiento de los temas dominados.",
    )


def build_hybrid_remaining_daily_plan(
    all_questions: List[Question],
    skills_map: Mapping[SkillKey, Skill],
    performance_map: Mapping[str, QuestionPerformance],
    completed_question_ids: set[str],
    daily_goal: int = 20,
    now: Optional[datetime] = None,
    max_official_cases: int = 2,
    diagnostic_min_attempts: int = DIAGNOSTIC_MIN_ATTEMPTS,
    diagnostic_share: float = 0.30,
) -> List[DailyRecommendation]:
    """Mix exam cases, coverage diagnosis, and adaptive reinforcement.

    Until a topic has enough answers, the plan reserves at least 30 percent of
    the available slots for distinct under-assessed topics. This prevents an
    early error in one subject from hiding an unmeasured subject indefinitely.
    """
    remaining_count = max(daily_goal - min(len(completed_question_ids), max(daily_goal, 0)), 0)
    if remaining_count == 0:
        return []

    eligible = [
        question for question in all_questions
        if question.question_id not in completed_question_ids
    ]
    ranked = build_daily_plan(
        eligible, skills_map, performance_map, n=len(eligible), now=now
    )
    by_id = {item.question.question_id: item for item in ranked}
    eligible_ids = set(by_id)
    selected = []
    selected_ids = set()
    selected_cases = set()

    # First guarantee breadth. One question per topic is intentional: the
    # diagnostic cycle needs evidence from different topics, not repetitions.
    attempts_by_topic = topic_attempt_counts(eligible, performance_map)
    diagnostic_items: dict[SkillKey, DailyRecommendation] = {}
    for item in ranked:
        key = _topic_key(item.question)
        if attempts_by_topic.get(key, 0) >= diagnostic_min_attempts:
            continue
        diagnostic_items.setdefault(key, item)

    diagnostic_slots = (
        min(
            len(diagnostic_items),
            max(1, math.ceil(remaining_count * diagnostic_share)),
        )
        if diagnostic_share > 0
        else 0
    )
    diagnostic_order = sorted(
        diagnostic_items.items(),
        key=lambda pair: (attempts_by_topic[pair[0]], -pair[1].score, pair[0]),
    )
    for _, item in diagnostic_order[:diagnostic_slots]:
        selected.append(
            DailyRecommendation(
                item.question,
                item.score,
                ("diagnóstico de cobertura",) + item.reasons,
            )
        )
        selected_ids.add(item.question.question_id)

    if remaining_count >= 3 and max_official_cases > 0:
        for item in ranked:
            case = getattr(item.question, "case_study", None)
            case_id = getattr(case, "id", None)
            if case is None or case_id in selected_cases:
                continue
            matching_group = next(
                (
                    group for group in official_question_groups(case)
                    if item.question.question_id in {q.question_id for q in group}
                ),
                None,
            )
            if not matching_group:
                continue
            group_ids = [question.question_id for question in matching_group]
            if not set(group_ids).issubset(eligible_ids):
                continue
            if set(group_ids) & selected_ids:
                continue
            if len(selected) + len(group_ids) > remaining_count:
                continue
            for question_id in group_ids:
                recommendation = by_id[question_id]
                selected.append(
                    DailyRecommendation(
                        recommendation.question,
                        recommendation.score,
                        ("caso tipo examen",) + recommendation.reasons,
                    )
                )
                selected_ids.add(question_id)
            selected_cases.add(case_id)
            if len(selected_cases) >= max_official_cases:
                break

    for item in ranked:
        if len(selected) >= remaining_count:
            break
        if item.question.question_id not in selected_ids:
            selected.append(item)
            selected_ids.add(item.question.question_id)
    return selected

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
    # Los casos verificados se mantienen como tripletas completas, como en el
    # formato GOA, antes de completar el cupo con preguntas adaptativas sueltas.
    from core.exam_format import official_question_groups

    selected = []
    selected_ids = set()
    seen_cases = set()
    case_groups = []
    eligible_ids = {question.question_id for question in all_questions}
    for question in all_questions:
        case = getattr(question, "case_study", None)
        case_id = getattr(case, "id", None)
        if not case_id or case_id in seen_cases:
            continue
        seen_cases.add(case_id)
        for group in official_question_groups(case):
            if {item.question_id for item in group}.issubset(eligible_ids):
                case_groups.append(group)
    random.shuffle(case_groups)
    for group in case_groups:
        if len(selected) + len(group) > n:
            continue
        selected.extend(group)
        selected_ids.update(question.question_id for question in group)

    remaining_n = n - len(selected)
    weak_questions = []
    medium_questions = []
    strong_questions = []

    for question in all_questions:
        if question.question_id in selected_ids:
            continue
        key = (question.track, question.competency, question.topic)
        skill = skills_map.get(key)
        mastery = skill.mastery_score if skill else 0.0

        if mastery < 50:
            weak_questions.append(question)
        elif mastery < 80:
            medium_questions.append(question)
        else:
            strong_questions.append(question)

    n_weak = int(remaining_n * 0.60)
    n_medium = int(remaining_n * 0.25)

    def sample_safe(pool, count):
        return random.sample(pool, min(len(pool), count))

    adaptive_selected = sample_safe(weak_questions, n_weak)
    remaining_weak_slots = n_weak - len(adaptive_selected)
    adaptive_selected.extend(sample_safe(medium_questions, n_medium + max(0, remaining_weak_slots)))
    adaptive_selected.extend(sample_safe(strong_questions, remaining_n - len(adaptive_selected)))

    if len(adaptive_selected) < remaining_n:
        remaining = [question for question in all_questions if question not in selected and question not in adaptive_selected]
        adaptive_selected.extend(sample_safe(remaining, remaining_n - len(adaptive_selected)))

    # No barajar internamente las tripletas; cada caso debe aparecer seguido.
    return selected + adaptive_selected
