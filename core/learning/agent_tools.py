"""Herramientas controladas para el tutor; ninguna acepta SQL libre."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import ProgrammingError, OperationalError

from db.models import LearningAttempt, LearningSession, NormativaChunk, Question, TopicMastery
from core.learning.session_service import LearningSessionService, question_view


class TutorTools:
    def __init__(self, db, *, user_id: int, competition_id: Optional[int]):
        self.db = db
        self.user_id = user_id
        self.competition_id = competition_id
        self.sessions = LearningSessionService(db)

    def _safe_query(self, fn, default=None):
        try:
            return fn()
        except (ProgrammingError, OperationalError):
            self.db.rollback()
            return default

    def get_learning_profile(self) -> dict:
        return self.sessions.learning_profile(self.user_id, self.competition_id)

    def get_current_session(self) -> Optional[dict]:
        def _query():
            row = self.db.query(LearningSession).filter_by(
                user_id=self.user_id, competition_id=self.competition_id, status="active"
            ).order_by(LearningSession.started_at.desc()).first()
            return self.sessions.get_session(row.id, self.user_id).model_dump() if row else None
        return self._safe_query(_query)

    def get_weak_topics(self, limit: int = 5) -> list[dict]:
        def _query():
            query = self.db.query(TopicMastery).filter_by(user_id=self.user_id)
            if self.competition_id is not None:
                query = query.filter(TopicMastery.competition_id == self.competition_id)
            return [
                {"topic_id": row.topic_id, "topic": row.topic_label, "mastery_score": row.mastery_score}
                for row in query.order_by(TopicMastery.mastery_score.asc()).limit(min(max(limit, 1), 20))
            ]
        return self._safe_query(_query, default=[])

    def get_due_reviews(self, limit: int = 10) -> list[dict]:
        def _query():
            query = self.db.query(TopicMastery).filter(
                TopicMastery.user_id == self.user_id,
                TopicMastery.next_review_at <= datetime.now(timezone.utc).replace(tzinfo=None),
            )
            if self.competition_id is not None:
                query = query.filter(TopicMastery.competition_id == self.competition_id)
            return [
                {"topic_id": row.topic_id, "topic": row.topic_label, "due_at": row.next_review_at.isoformat()}
                for row in query.order_by(TopicMastery.next_review_at).limit(min(max(limit, 1), 50))
            ]
        return self._safe_query(_query, default=[])

    def get_recent_errors(self, limit: int = 10) -> list[dict]:
        def _query():
            query = self.db.query(LearningAttempt).join(
                Question, LearningAttempt.question_id == Question.question_id
            ).filter(
                LearningAttempt.user_id == self.user_id,
                LearningAttempt.result != "correct",
            )
            if self.competition_id is not None:
                query = query.filter(Question.competition_id == self.competition_id)
            rows = query.order_by(LearningAttempt.created_at.desc()).limit(
                min(max(limit, 1), 50)
            ).all()
            return [
                {
                    "question_id": row.question_id,
                    "result": row.result,
                    "error_type": row.error_type,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        return self._safe_query(_query, default=[])

    def get_topic_mastery(self, topic_id: str) -> Optional[dict]:
        def _query():
            row = self.db.query(TopicMastery).filter_by(
                user_id=self.user_id, competition_id=self.competition_id, topic_id=topic_id
            ).first()
            return None if row is None else {
                "topic_id": row.topic_id,
                "topic": row.topic_label,
                "mastery_score": row.mastery_score,
                "attempts": row.attempts,
                "next_review_at": row.next_review_at.isoformat() if row.next_review_at else None,
            }
        return self._safe_query(_query)

    def get_question(self, question_id: str) -> Optional[dict]:
        row = self.db.get(Question, question_id)
        if row is None or (
            self.competition_id is not None and row.competition_id != self.competition_id
        ):
            return None
        return question_view(row).model_dump()

    def register_attempt(self, **payload):
        return self.sessions.submit_answer(user_id=self.user_id, **payload)

    def search_learning_material(self, query: str, limit: int = 5) -> list[dict]:
        clean_query = " ".join(str(query).split())[:120]
        if len(clean_query) < 3:
            return []
        rows = self.db.query(NormativaChunk).filter(
            NormativaChunk.content.ilike(f"%{clean_query}%")
        ).limit(min(max(limit, 1), 10)).all()
        return [
            {"source": row.source_file, "page": row.page, "excerpt": row.content[:700]}
            for row in rows
        ]

    def finish_session(self, session_id: str):
        return self.sessions.finish_session(session_id, self.user_id)
