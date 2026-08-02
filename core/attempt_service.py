"""Registro único de respuestas para todos los modos de estudio.

Mantiene alineados el historial bruto, el rendimiento por pregunta, la
habilidad y la cola de repaso espaciado. Las páginas pueden usar este servicio
sin duplicar reglas de actualización.
"""
from datetime import datetime
from typing import Optional

from db.models import Attempt, Question, QuestionPerformance, Skill
from core.spaced_repetition import schedule_review


def record_attempt(
    db,
    *,
    user_id: int,
    question: Question,
    chosen_key: str,
    confidence: str = "unsure",
    error_type: Optional[str] = None,
    time_sec: Optional[int] = None,
    when: Optional[datetime] = None,
) -> bool:
    """Persiste una respuesta y actualiza todo el estado adaptativo.

    Devuelve si la respuesta fue correcta. El commit queda a cargo del flujo
    que agrupa la sesión, permitiendo guardar un simulacro como unidad.
    """
    now = when or datetime.utcnow()
    is_correct = chosen_key == question.correct_key
    db.add(Attempt(
        question_id=question.question_id,
        user_id=user_id,
        chosen_key=chosen_key,
        is_correct=is_correct,
        time_sec=time_sec,
        created_at=now,
    ))

    perf = db.query(QuestionPerformance).filter_by(
        user_id=user_id, question_id=question.question_id
    ).first()
    if perf is None:
        perf = QuestionPerformance(user_id=user_id, question_id=question.question_id)
        db.add(perf)
        db.flush()
    perf.hits = int(perf.hits or 0) + int(is_correct)
    perf.misses = int(perf.misses or 0) + int(not is_correct)
    perf.mastery_level = (perf.hits / max(perf.hits + perf.misses, 1)) * 10.0
    perf.last_attempt = now
    schedule_review(perf, is_correct=is_correct, confidence=confidence,
                    error_type=error_type, now=now)

    skill = db.query(Skill).filter_by(
        user_id=user_id, competition_id=question.competition_id,
        track=question.track, competency=question.competency, topic=question.topic,
    ).first()
    if skill is None:
        skill = Skill(user_id=user_id, competition_id=question.competition_id,
                      track=question.track, competency=question.competency,
                      topic=question.topic, mastery_score=0.0, priority_weight=1.0)
        db.add(skill)
    current = float(skill.mastery_score or 0.0)
    skill.mastery_score = min(100.0, current + 5.0 * ((100.0 - current) / 100.0)) if is_correct else max(0.0, current - 10.0)
    skill.priority_weight = max(1.0, float(skill.priority_weight or 1.0) - 0.5) if is_correct else float(skill.priority_weight or 1.0) + 2.0
    skill.last_seen = now
    return is_correct
