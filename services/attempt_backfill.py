"""Reconstrucción de rendimiento adaptativo a partir del historial de intentos."""
from collections import defaultdict

from db.models import Attempt, Question, QuestionPerformance, Skill


def backfill_attempt_performance(db, user_id: int) -> dict:
    """Sincroniza los agregados de un usuario sin hacer commit.

    Es idempotente: repetirlo produce los mismos contadores porque estos se
    recalculan desde los intentos persistidos, en lugar de incrementarse.
    """
    attempts = db.query(Attempt).filter(Attempt.user_id == user_id).all()
    grouped = defaultdict(lambda: {"hits": 0, "misses": 0, "last_attempt": None})
    for attempt in attempts:
        item = grouped[attempt.question_id]
        item["hits"] += int(bool(attempt.is_correct))
        item["misses"] += int(not bool(attempt.is_correct))
        if item["last_attempt"] is None or attempt.created_at > item["last_attempt"]:
            item["last_attempt"] = attempt.created_at

    created = updated = 0
    for question_id, totals in grouped.items():
        performance = db.query(QuestionPerformance).filter_by(
            user_id=user_id, question_id=question_id
        ).first()
        if performance is None:
            performance = QuestionPerformance(user_id=user_id, question_id=question_id)
            db.add(performance)
            created += 1
        else:
            updated += 1
        performance.hits = totals["hits"]
        performance.misses = totals["misses"]
        total = totals["hits"] + totals["misses"]
        performance.mastery_level = (totals["hits"] / total * 10.0) if total else 0.0
        performance.is_mastered = total >= 5 and performance.mastery_level >= 7.5
        performance.last_attempt = totals["last_attempt"]

    skill_totals = defaultdict(lambda: {"hits": 0, "misses": 0, "last_attempt": None})
    questions = {
        row.question_id: row for row in db.query(Question).filter(
            Question.question_id.in_(list(grouped))
        ).all()
    } if grouped else {}
    for question_id, totals in grouped.items():
        question = questions.get(question_id)
        if not question:
            continue
        key = (
            question.competition_id, question.track, question.competency, question.topic,
        )
        aggregate = skill_totals[key]
        aggregate["hits"] += totals["hits"]
        aggregate["misses"] += totals["misses"]
        if aggregate["last_attempt"] is None or totals["last_attempt"] > aggregate["last_attempt"]:
            aggregate["last_attempt"] = totals["last_attempt"]

    created_skills = updated_skills = 0
    for key, totals in skill_totals.items():
        competition_id, track, competency, topic = key
        skill = db.query(Skill).filter_by(
            user_id=user_id, competition_id=competition_id,
            track=track, competency=competency, topic=topic,
        ).first()
        if skill is None:
            skill = Skill(user_id=user_id, competition_id=competition_id,
                          track=track, competency=competency, topic=topic)
            db.add(skill)
            created_skills += 1
        else:
            updated_skills += 1
        total = totals["hits"] + totals["misses"]
        error_rate = totals["misses"] / total if total else 0.0
        skill.mastery_score = totals["hits"] / total * 100.0 if total else 0.0
        skill.priority_weight = min(3.0, 1.0 + 2.0 * error_rate)
        skill.last_seen = totals["last_attempt"]

    return {
        "attempts": len(attempts),
        "questions": len(grouped),
        "created": created,
        "updated": updated,
        "created_skills": created_skills,
        "updated_skills": updated_skills,
    }
