"""Casos de uso transaccionales para sesiones adaptativas."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from core.learning.engine import (
    calculate_mastery,
    calculate_topic_priority,
    schedule_next_review,
    select_next_question,
    topic_id_for,
)
from core.learning.schemas import (
    ConfidenceLevel,
    ErrorType,
    EvaluationResult,
    LearningResult,
    QuestionView,
    SessionView,
    SubmissionResult,
)
from core.spaced_repetition import schedule_review as schedule_legacy_review
from db.models import (
    Attempt,
    LearningAttempt,
    LearningSession,
    Question,
    QuestionPerformance,
    Skill,
    TopicMastery,
)


CONFIDENCE_TO_LEGACY = {"low": "guess", "medium": "unsure", "high": "confident"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def question_view(question: Optional[Question]) -> Optional[QuestionView]:
    if question is None:
        return None
    return QuestionView(
        question_id=str(question.question_id),
        stem=question.stem,
        options=dict(question.options_json or {}),
        topic=question.topic or "Sin tema",
        competency=question.competency or "General",
        difficulty=int(question.difficulty or 2),
    )


class LearningSessionService:
    def __init__(self, db):
        self.db = db

    def _questions(self, competition_id: Optional[int]) -> list[Question]:
        query = self.db.query(Question)
        if competition_id is not None:
            query = query.filter(Question.competition_id == competition_id)
        return query.order_by(Question.question_id).all()

    def _topic_priorities(self, user_id: int, competition_id: Optional[int], questions, now):
        mastery_query = self.db.query(TopicMastery).filter(TopicMastery.user_id == user_id)
        if competition_id is not None:
            mastery_query = mastery_query.filter(TopicMastery.competition_id == competition_id)
        mastery_map = {row.topic_id: row for row in mastery_query.all()}

        recent_query = self.db.query(LearningAttempt).filter(LearningAttempt.user_id == user_id)
        if competition_id is not None:
            recent_query = recent_query.join(Question).filter(Question.competition_id == competition_id)
        recent = recent_query.order_by(LearningAttempt.created_at.desc()).limit(50).all()
        question_by_id = {str(q.question_id): q for q in questions}
        stats = defaultdict(lambda: {"total": 0, "errors": 0, "low": 0})
        for attempt in recent:
            question = question_by_id.get(str(attempt.question_id))
            if question is None:
                continue
            topic_id = topic_id_for(question.track, question.competency, question.topic)
            stats[topic_id]["total"] += 1
            stats[topic_id]["errors"] += int(attempt.result != "correct")
            stats[topic_id]["low"] += int(attempt.confidence == "low")

        priorities = {}
        for question in questions:
            topic_id = topic_id_for(question.track, question.competency, question.topic)
            if topic_id in priorities:
                continue
            mastery = mastery_map.get(topic_id)
            topic_stats = stats[topic_id]
            total = max(topic_stats["total"], 1)
            priorities[topic_id] = calculate_topic_priority(
                mastery_score=float(mastery.mastery_score if mastery else 0.0),
                next_review_at=mastery.next_review_at if mastery else None,
                recent_error_rate=topic_stats["errors"] / total if topic_stats["total"] else 0.5,
                low_confidence_rate=topic_stats["low"] / total if topic_stats["total"] else 0.5,
                importance=float(mastery.importance if mastery else 1.0),
                last_studied_at=mastery.last_reviewed_at if mastery else None,
                now=now,
            )
        return priorities

    def _select(self, session: LearningSession, now: datetime):
        questions = self._questions(session.competition_id)
        priorities = self._topic_priorities(session.user_id, session.competition_id, questions, now)
        attempted_ids = {
            str(row[0])
            for row in self.db.query(LearningAttempt.question_id)
            .filter(LearningAttempt.session_id == session.id)
            .all()
        }
        selected = select_next_question(questions, priorities, excluded_question_ids=attempted_ids)
        if selected is None and questions:
            selected = select_next_question(
                questions,
                priorities,
                excluded_question_ids={str(session.current_question_id)} if session.current_question_id else set(),
            )
        return selected

    def start_learning_session(
        self,
        *,
        user_id: int,
        target_minutes: int,
        competition_id: Optional[int],
        now: Optional[datetime] = None,
    ) -> SessionView:
        if not 5 <= int(target_minutes) <= 180:
            raise ValueError("La sesión debe durar entre 5 y 180 minutos")
        now = now or utc_now()
        active = self.db.query(LearningSession).filter_by(
            user_id=user_id, competition_id=competition_id, status="active"
        ).all()
        for previous in active:
            previous.status = "abandoned"
            previous.finished_at = now
            previous.actual_minutes = max(0, int((now - previous.started_at).total_seconds() // 60))

        session = LearningSession(
            user_id=user_id,
            competition_id=competition_id,
            started_at=now,
            target_minutes=int(target_minutes),
            status="active",
        )
        self.db.add(session)
        self.db.flush()
        selected = self._select(session, now)
        session.current_question_id = selected.question_id if selected else None
        self.db.commit()
        return SessionView(
            session_id=session.id,
            status=session.status,
            target_minutes=session.target_minutes,
            started_at=session.started_at,
            question=question_view(selected),
        )

    def get_session(self, session_id: str, user_id: int) -> Optional[SessionView]:
        session = self.db.query(LearningSession).filter_by(id=session_id, user_id=user_id).first()
        if session is None:
            return None
        return SessionView(
            session_id=session.id,
            status=session.status,
            target_minutes=session.target_minutes,
            started_at=session.started_at,
            question=question_view(self.db.get(Question, session.current_question_id)),
        )

    def submit_answer(
        self,
        *,
        session_id: str,
        user_id: int,
        answer: str,
        confidence: str,
        response_time_seconds: Optional[int] = None,
        result_override: Optional[str] = None,
        error_type: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> SubmissionResult:
        now = now or utc_now()
        confidence = ConfidenceLevel(confidence).value
        session = self.db.query(LearningSession).filter_by(
            id=session_id, user_id=user_id, status="active"
        ).first()
        if session is None or not session.current_question_id:
            raise ValueError("No existe una sesión activa con pregunta pendiente")
        question = self.db.get(Question, session.current_question_id)
        if question is None:
            raise ValueError("La pregunta activa ya no existe")

        result = (
            LearningResult(result_override).value
            if result_override
            else ("correct" if answer == question.correct_key else "incorrect")
        )
        score = {"correct": 1.0, "partial": 0.6, "incorrect": 0.0}[result]
        if result == "correct":
            error_type = None
        elif error_type is None:
            error_type = "overconfidence" if confidence == "high" else "distractor"
        if error_type is not None:
            error_type = ErrorType(error_type).value

        topic_id = topic_id_for(question.track, question.competency, question.topic)
        mastery = self.db.query(TopicMastery).filter_by(
            user_id=user_id,
            competition_id=question.competition_id,
            topic_id=topic_id,
        ).first()
        if mastery is None:
            mastery = TopicMastery(
                user_id=user_id,
                competition_id=question.competition_id,
                topic_id=topic_id,
                topic_label=question.topic or "Sin tema",
                competency=question.competency,
                track=question.track,
                mastery_score=0.0,
                importance=1.0,
            )
            self.db.add(mastery)
            self.db.flush()
        mastery.mastery_score = calculate_mastery(mastery.mastery_score or 0.0, result, confidence)
        mastery.attempts = int(mastery.attempts or 0) + 1
        mastery.correct_attempts = int(mastery.correct_attempts or 0) + int(result == "correct")
        mastery.partial_attempts = int(mastery.partial_attempts or 0) + int(result == "partial")
        mastery.last_reviewed_at = now
        mastery.next_review_at = schedule_next_review(
            result, confidence, mastery.mastery_score, now=now
        )
        mastery.updated_at = now

        self.db.add(LearningAttempt(
            session_id=session.id,
            user_id=user_id,
            question_id=question.question_id,
            answer=answer,
            result=result,
            score=score,
            confidence=confidence,
            error_type=error_type,
            response_time_seconds=response_time_seconds,
            created_at=now,
        ))
        self.db.add(Attempt(
            user_id=user_id,
            question_id=question.question_id,
            chosen_key=answer,
            is_correct=result == "correct",
            time_sec=response_time_seconds,
            created_at=now,
        ))

        performance = self.db.query(QuestionPerformance).filter_by(
            user_id=user_id, question_id=question.question_id
        ).first()
        if performance is None:
            performance = QuestionPerformance(user_id=user_id, question_id=question.question_id)
            self.db.add(performance)
            self.db.flush()
        performance.hits = int(performance.hits or 0) + int(result == "correct")
        performance.misses = int(performance.misses or 0) + int(result != "correct")
        performance.mastery_level = mastery.mastery_score / 10.0
        performance.last_attempt = now
        schedule_legacy_review(
            performance,
            is_correct=result == "correct",
            confidence=CONFIDENCE_TO_LEGACY[confidence],
            error_type=error_type,
            now=now,
        )

        skill = self.db.query(Skill).filter_by(
            user_id=user_id,
            competition_id=question.competition_id,
            track=question.track,
            competency=question.competency,
            topic=question.topic,
        ).first()
        if skill is None:
            skill = Skill(
                user_id=user_id,
                competition_id=question.competition_id,
                track=question.track,
                competency=question.competency,
                topic=question.topic,
                mastery_score=mastery.mastery_score,
                priority_weight=1.0,
            )
            self.db.add(skill)
        skill.mastery_score = mastery.mastery_score
        skill.last_seen = now
        skill.updated_at = now

        next_question = self._select(session, now)
        session.current_question_id = next_question.question_id if next_question else None
        self.db.commit()
        feedback = question.rationale or (
            "Respuesta correcta." if result == "correct" else "Revisa el criterio central de este tema."
        )
        return SubmissionResult(
            evaluation=EvaluationResult(
                result=result,
                score=score,
                error_type=error_type,
                feedback=feedback,
                needs_review=result != "correct" or confidence == "low",
            ),
            next_question=question_view(next_question),
            mastery_score=mastery.mastery_score,
            next_review_at=mastery.next_review_at,
        )

    def finish_session(
        self, session_id: str, user_id: int, *, now: Optional[datetime] = None
    ) -> LearningSession:
        now = now or utc_now()
        session = self.db.query(LearningSession).filter_by(id=session_id, user_id=user_id).first()
        if session is None:
            raise ValueError("Sesión no encontrada")
        session.finished_at = session.finished_at or now
        session.actual_minutes = max(0, int((session.finished_at - session.started_at).total_seconds() // 60))
        session.status = "completed"
        session.current_question_id = None
        self.db.commit()
        return session

    def learning_profile(self, user_id: int, competition_id: Optional[int], now=None) -> dict:
        now = now or utc_now()
        query = self.db.query(TopicMastery).filter(TopicMastery.user_id == user_id)
        if competition_id is not None:
            query = query.filter(TopicMastery.competition_id == competition_id)
        topics = query.order_by(TopicMastery.mastery_score.asc()).all()
        general = sum(row.mastery_score or 0 for row in topics) / len(topics) if topics else 0.0
        due = sum(1 for row in topics if row.next_review_at is None or row.next_review_at <= now)
        return {
            "general_mastery": round(general, 1),
            "weakest_topic": topics[0].topic_label if topics else "Aún sin diagnóstico",
            "due_reviews": due,
            "topics": topics,
            "recommendation": (
                f"Empieza por {topics[0].topic_label}." if topics else "Inicia una sesión diagnóstica."
            ),
        }
