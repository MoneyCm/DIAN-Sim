"""Casos de uso transaccionales para sesiones adaptativas."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
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
from core.learning.evidence_service import (
    finalize_opec_session,
    record_opec_event,
    start_opec_session,
)
from services.question_service import QuestionService
from db.models import (
    Attempt,
    LearningAttempt,
    LearningSession,
    OpecLearningEvent,
    OpecLearningSession,
    OpecTopicState,
    Question,
    QuestionPerformance,
    Skill,
    TopicMastery,
    UserOPEC,
)


CONFIDENCE_TO_LEGACY = {"low": "guess", "medium": "unsure", "high": "confident"}


@dataclass(frozen=True)
class TutorTopicProfile:
    """UI-compatible projection of canonical, OPEC-scoped topic evidence."""

    topic_id: str
    topic_label: str
    competency: Optional[str]
    track: Optional[str]
    mastery_score: float
    attempts: int
    last_reviewed_at: Optional[datetime]
    next_review_at: Optional[datetime]


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
        self._legacy_schema_available: Optional[bool] = None

    def _legacy_schema_available_for_learning(self) -> bool:
        """Detect once whether legacy session tables exist in the active DB."""
        if self._legacy_schema_available is not None:
            return self._legacy_schema_available
        try:
            self.db.execute(text("SELECT 1 FROM learning_sessions LIMIT 1"))
            # Legacy OPEC + adaptive flow in this service also depends on
            # TopicMastery persistence when using LearningSession/attempts.
            # If TopicMastery no longer exists (new deployments), avoid forcing
            # the legacy branch and fall back to OPEC-only adaptive mode.
            self.db.execute(text("SELECT 1 FROM topic_mastery LIMIT 1"))
            self._legacy_schema_available = True
        except (OperationalError, ProgrammingError):
            self.db.rollback()
            self._legacy_schema_available = False
        return self._legacy_schema_available

    def _active_opec(
        self, user_id: int, competition_id: Optional[int]
    ) -> Optional[UserOPEC]:
        """Resolve one active OPEC; ambiguity is treated as no safe context."""
        query = self.db.query(UserOPEC).filter_by(user_id=user_id, is_active=True)
        if competition_id is not None:
            query = query.filter(UserOPEC.competition_id == competition_id)
        try:
            rows = query.order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc()).all()
        except (OperationalError, ProgrammingError):
            self.db.rollback()
            return None
        return rows[0] if len(rows) == 1 else None

    def _questions(
        self,
        competition_id: Optional[int],
        user_id: Optional[int] = None,
        *,
        user_opec: Optional[UserOPEC] = None,
    ) -> list[Question]:
        """Return only reviewed training questions in the exact active OPEC."""
        if user_id is None or competition_id is None:
            return []
        active_opec = user_opec or self._active_opec(user_id, competition_id)
        if (
            active_opec is None
            or active_opec.user_id != user_id
            or active_opec.competition_id != competition_id
            or not active_opec.is_active
        ):
            return []
        questions = QuestionService.get_questions_for_user(
            self.db,
            user_id,
            competition_id=competition_id,
            user_opec=active_opec,
            bank_partitions=("training",),
        )
        # QuestionService owns the complete delivery decision: canonical
        # evidence for explicitly scoped banks, or the conservative legacy
        # quality gate when canonical scoping is unavailable. Reapplying the
        # legacy gate here would incorrectly reject canonically approved items.
        return sorted(
            questions,
            key=lambda question: str(question.question_id),
        )

    def _canonical_session(
        self, session: LearningSession
    ) -> Optional[OpecLearningSession]:
        rows = (
            self.db.query(OpecLearningSession)
            .filter_by(
                user_id=session.user_id,
                competition_id=session.competition_id,
            )
            .order_by(OpecLearningSession.started_at.desc())
            .all()
        )
        for row in rows:
            coverage = row.coverage if isinstance(row.coverage, dict) else {}
            if str(coverage.get("legacy_session_id", "")) == str(session.id):
                return row
        return None

    @staticmethod
    def _session_current_question_id(session) -> Optional[str]:
        if hasattr(session, "current_question_id") and session.current_question_id:
            return str(session.current_question_id)
        if isinstance(session, OpecLearningSession):
            coverage = session.coverage if isinstance(session.coverage, dict) else {}
            question_id = coverage.get("current_question_id")
            return str(question_id) if question_id is not None else None
        return None

    @staticmethod
    def _set_session_current_question_id(session, question_id: Optional[str]) -> None:
        if hasattr(session, "current_question_id"):
            session.current_question_id = question_id
            return
        if isinstance(session, OpecLearningSession):
            coverage = session.coverage if isinstance(session.coverage, dict) else {}
            if question_id is None:
                coverage.pop("current_question_id", None)
            else:
                coverage["current_question_id"] = str(question_id)
            session.coverage = coverage

    def _invalidate_context(
        self,
        session: LearningSession,
        canonical: Optional[OpecLearningSession],
        now: datetime,
    ) -> None:
        session.status = "abandoned"
        session.current_question_id = None
        session.finished_at = session.finished_at or now
        session.actual_minutes = max(
            0, int((session.finished_at - session.started_at).total_seconds() // 60)
        )
        if canonical is not None and canonical.status == "active":
            canonical.status = "invalid"
            canonical.completed_at = now

    def _invalidate_opec_context(
        self,
        session: OpecLearningSession,
        now: datetime,
    ) -> None:
        if session.status == "active":
            session.status = "abandoned"
            session.completed_at = now

    def _validated_context(
        self,
        session: LearningSession,
        now: datetime,
    ) -> tuple[Optional[OpecLearningSession], Optional[UserOPEC], list[Question]]:
        """Validate the immutable OPEC snapshot before showing or recording."""
        canonical = self._canonical_session(session)
        active_opec = self._active_opec(session.user_id, session.competition_id)
        if (
            canonical is None
            or active_opec is None
            or canonical.status != "active"
            or canonical.user_opec_id != active_opec.id
            or canonical.competition_id != active_opec.competition_id
            or str(canonical.opec_number) != str(active_opec.opec_number)
        ):
            self._invalidate_context(session, canonical, now)
            return canonical, active_opec, []

        questions = self._questions(
            session.competition_id,
            session.user_id,
            user_opec=active_opec,
        )
        eligible_ids = {str(question.question_id) for question in questions}
        coverage = canonical.coverage if isinstance(canonical.coverage, dict) else {}
        snapshot_ids = {str(value) for value in coverage.get("question_ids", [])}
        current_id = str(session.current_question_id) if session.current_question_id else None
        if (
            not snapshot_ids
            or not snapshot_ids.issubset(eligible_ids)
            or (current_id is not None and current_id not in snapshot_ids)
        ):
            self._invalidate_context(session, canonical, now)
            return canonical, active_opec, []
        return canonical, active_opec, questions

    def _validated_opec_context(
        self,
        session: OpecLearningSession,
        now: datetime,
    ) -> tuple[OpecLearningSession, Optional[UserOPEC], list[Question]]:
        active_opec = self._active_opec(session.user_id, session.competition_id)
        questions = self._questions(
            session.competition_id,
            session.user_id,
            user_opec=active_opec,
        )
        eligibility_ids = {str(question.question_id) for question in questions}
        coverage = session.coverage if isinstance(session.coverage, dict) else {}
        snapshot_ids = {str(value) for value in coverage.get("question_ids", [])}
        current_id = self._session_current_question_id(session)
        if (
            active_opec is None
            or session.status != "active"
            or str(session.opec_number) != str(active_opec.opec_number)
            or session.user_opec_id != active_opec.id
            or session.competition_id != active_opec.competition_id
            or not snapshot_ids
            or not snapshot_ids.issubset(eligibility_ids)
            or (current_id is not None and current_id not in snapshot_ids)
        ):
            self._invalidate_opec_context(session, now)
            return session, active_opec, []
        return session, active_opec, questions

    def _topic_priorities(
        self,
        user_id: int,
        competition_id: Optional[int],
        user_opec: UserOPEC,
        questions,
        now,
    ):
        try:
            mastery_rows = self.db.query(OpecTopicState).filter_by(
                user_id=user_id,
                competition_id=competition_id,
                user_opec_id=user_opec.id,
            ).all()
            recent = (
                self.db.query(OpecLearningEvent)
                .join(OpecLearningSession)
                .filter(
                    OpecLearningEvent.user_id == user_id,
                    OpecLearningSession.competition_id == competition_id,
                    OpecLearningSession.user_opec_id == user_opec.id,
                )
                .order_by(OpecLearningEvent.created_at.desc())
                .limit(50)
                .all()
            )
        except (OperationalError, ProgrammingError):
            self.db.rollback()
            mastery_rows = []
            recent = []
        mastery_map = {row.topic_id: row for row in mastery_rows}
        eligible_topic_ids = {
            topic_id_for(question.track, question.competency, question.topic)
            for question in questions
        }
        stats = defaultdict(lambda: {"total": 0, "errors": 0, "low": 0})
        for event in recent:
            if event.topic_id not in eligible_topic_ids or event.is_correct is None:
                continue
            stats[event.topic_id]["total"] += 1
            stats[event.topic_id]["errors"] += int(event.is_correct is False)
            stats[event.topic_id]["low"] += int(event.confidence == "low")

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
                recent_error_rate=(
                    topic_stats["errors"] / total if topic_stats["total"] else 0.5
                ),
                low_confidence_rate=(
                    topic_stats["low"] / total if topic_stats["total"] else 0.5
                ),
                importance=1.0,
                last_studied_at=mastery.last_event_at if mastery else None,
                now=now,
            )
        return priorities

    def _load_profile_states(self, user_id: int, competition_id: Optional[int], active_opec: UserOPEC):
        """Load progress states for profile chart with legacy compatibility."""
        try:
            return (
                self.db.query(OpecTopicState)
                .filter_by(
                    user_id=user_id,
                    competition_id=competition_id,
                    user_opec_id=active_opec.id,
                )
                .order_by(OpecTopicState.mastery_score.asc())
                .all()
            )
        except (OperationalError, ProgrammingError):
            self.db.rollback()
            try:
                return (
                    self.db.query(TopicMastery)
                    .filter_by(user_id=user_id, competition_id=competition_id)
                    .order_by(TopicMastery.mastery_score.asc())
                    .all()
                )
            except (OperationalError, ProgrammingError):
                self.db.rollback()
                return []

    def _select(self, session, now: datetime):
        active_opec = self._active_opec(session.user_id, session.competition_id)
        if active_opec is None:
            return None
        questions = self._questions(
            session.competition_id,
            session.user_id,
            user_opec=active_opec,
        )
        priorities = self._topic_priorities(
            session.user_id,
            session.competition_id,
            active_opec,
            questions,
            now,
        )
        mastery_rows = (
            self.db.query(OpecTopicState)
            .filter_by(
                user_id=session.user_id,
                competition_id=session.competition_id,
                user_opec_id=active_opec.id,
            )
            .all()
        )
        mastery_scores = {
            row.topic_id: float(row.mastery_score or 0.0) for row in mastery_rows
        }
        mastery_attempts = {
            row.topic_id: int(row.evidence_count or 0) for row in mastery_rows
        }
        if isinstance(session, LearningSession):
            attempted_ids = {
                str(row[0])
                for row in self.db.query(LearningAttempt.question_id)
                .filter(LearningAttempt.session_id == session.id)
                .all()
            }
        else:
            try:
                attempted_ids = {
                    str(row[0])
                    for row in self.db.query(OpecLearningEvent.question_id)
                    .filter(OpecLearningEvent.session_id == session.id)
                    .all()
                }
            except (OperationalError, ProgrammingError):
                self.db.rollback()
                attempted_ids = set()
        selected = select_next_question(
            questions, priorities, excluded_question_ids=attempted_ids,
            topic_mastery_scores=mastery_scores, topic_attempt_counts=mastery_attempts,
        )
        if selected is None and questions:
            current_id = self._session_current_question_id(session)
            selected = select_next_question(
                questions,
                priorities,
                excluded_question_ids={str(current_id)} if current_id else set(),
                topic_mastery_scores=mastery_scores,
                topic_attempt_counts=mastery_attempts,
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
        active_opec: Optional[UserOPEC] = None
        eligible_questions: list[Question] = []
        try:
            if self._legacy_schema_available_for_learning():
                try:
                    active_opec = self._active_opec(user_id, competition_id)
                    eligible_questions = self._questions(
                        competition_id,
                        user_id,
                        user_opec=active_opec,
                    )
                    return self._start_learning_session_legacy(
                        user_id=user_id,
                        target_minutes=target_minutes,
                        competition_id=competition_id,
                        now=now,
                        active_opec=active_opec,
                        eligible_questions=eligible_questions,
                    )
                except (OperationalError, ProgrammingError):
                    self.db.rollback()
                    self._legacy_schema_available = False
                    active_opec = None
                    eligible_questions = []

            active_opec = self._active_opec(user_id, competition_id)
            eligible_questions = self._questions(
                competition_id,
                user_id,
                user_opec=active_opec,
            )
            return self._start_learning_session_opec(
                user_id=user_id,
                target_minutes=target_minutes,
                competition_id=competition_id,
                now=now,
                active_opec=active_opec,
                eligible_questions=eligible_questions,
            )
        except (OperationalError, ProgrammingError):
            self.db.rollback()
            return SessionView(
                session_id="",
                status="inactive",
                target_minutes=int(target_minutes),
                started_at=now,
                question=None,
            )

    def _start_learning_session_legacy(
        self,
        *,
        user_id: int,
        target_minutes: int,
        competition_id: Optional[int],
        now: datetime,
        active_opec: Optional[UserOPEC],
        eligible_questions: list[Question],
    ) -> SessionView:
        active = self.db.query(LearningSession).filter_by(
            user_id=user_id, competition_id=competition_id, status="active"
        ).all()
        for previous in active:
            previous.status = "abandoned"
            previous.finished_at = now
            previous.actual_minutes = max(0, int((now - previous.started_at).total_seconds() // 60))
            previous_canonical = self._canonical_session(previous)
            if previous_canonical is not None and previous_canonical.status == "active":
                previous_canonical.status = "abandoned"
                previous_canonical.completed_at = now

        session = LearningSession(
            user_id=user_id,
            competition_id=competition_id,
            started_at=now,
            target_minutes=int(target_minutes),
            status="active",
        )
        self.db.add(session)
        self.db.flush()
        canonical = None
        if active_opec is not None and eligible_questions:
            canonical = start_opec_session(
                self.db,
                user_id=user_id,
                questions=eligible_questions,
                mode="training",
                bank_partition="training",
                competition_id=competition_id,
                user_opec_id=active_opec.id,
                feedback_enabled=True,
                now=now,
            )
            coverage = dict(canonical.coverage or {})
            coverage.update({
                "legacy_session_id": str(session.id),
                "target_minutes": int(target_minutes),
            })
            canonical.coverage = coverage
        selected = self._select(session, now) if canonical is not None else None
        session.current_question_id = selected.question_id if selected else None
        self.db.commit()
        return SessionView(
            session_id=session.id,
            status=session.status,
            target_minutes=session.target_minutes,
            started_at=session.started_at,
            question=question_view(selected),
        )

    def _start_learning_session_opec(
        self,
        *,
        user_id: int,
        target_minutes: int,
        competition_id: Optional[int],
        now: datetime,
        active_opec: Optional[UserOPEC],
        eligible_questions: list[Question],
    ) -> SessionView:
        if active_opec is None or not eligible_questions:
            return SessionView(
                session_id="",
                status="inactive",
                target_minutes=int(target_minutes),
                started_at=now,
                question=None,
            )
        active = self.db.query(OpecLearningSession).filter_by(
            user_id=user_id,
            competition_id=competition_id,
            status="active",
        ).all()
        for previous in active:
            previous.status = "abandoned"
            previous.completed_at = now

        canonical = start_opec_session(
            self.db,
            user_id=user_id,
            questions=eligible_questions,
            mode="training",
            bank_partition="training",
            competition_id=competition_id,
            user_opec_id=active_opec.id,
            feedback_enabled=True,
            now=now,
        )
        coverage = dict(canonical.coverage or {})
        coverage.update({
            "legacy_session_id": None,
            "target_minutes": int(target_minutes),
        })
        selected = self._select(canonical, now) if active_opec is not None else None
        if selected is not None:
            coverage["current_question_id"] = str(selected.question_id)
        else:
            coverage.pop("current_question_id", None)
        canonical.coverage = coverage
        self._set_session_current_question_id(canonical, selected.question_id if selected else None)
        self.db.commit()
        return SessionView(
            session_id=canonical.id,
            status=canonical.status,
            target_minutes=int(target_minutes),
            started_at=canonical.started_at,
            question=question_view(selected),
        )

    def get_session(self, session_id: str, user_id: int) -> Optional[SessionView]:
        if self._legacy_schema_available_for_learning():
            try:
                session = self.db.query(LearningSession).filter_by(
                    id=session_id, user_id=user_id
                ).first()
                if session is None:
                    return None
                question = None
                if session.status == "active":
                    self._validated_context(session, utc_now())
                    if session.status != "active":
                        self.db.commit()
                    elif session.current_question_id:
                        question = self.db.get(Question, session.current_question_id)
                return SessionView(
                    session_id=session.id,
                    status=session.status,
                    target_minutes=session.target_minutes,
                    started_at=session.started_at,
                    question=question_view(question),
                )
            except (OperationalError, ProgrammingError):
                self.db.rollback()
                self._legacy_schema_available = False

        session = self.db.get(OpecLearningSession, session_id)
        if session is None:
            return None
        question = None
        if session.status == "active":
            session, _active_opec, _questions = self._validated_opec_context(session, utc_now())
            if session.status != "active":
                self.db.commit()
            else:
                current_id = self._session_current_question_id(session)
                if current_id:
                    question = self.db.get(Question, current_id)
        coverage = session.coverage if isinstance(session.coverage, dict) else {}
        return SessionView(
            session_id=session.id,
            status=session.status,
            target_minutes=int(
                coverage.get("target_minutes") or 0
            ),
            started_at=session.started_at,
            question=question_view(question),
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
        user_reasoning: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> SubmissionResult:
        now = now or utc_now()
        if confidence is None or not str(confidence).strip():
            raise ValueError("Declara tu nivel de confianza antes de responder")
        confidence = ConfidenceLevel(confidence).value
        if response_time_seconds is not None and int(response_time_seconds) < 0:
            raise ValueError("El tiempo de respuesta no puede ser negativo")
        if self._legacy_schema_available_for_learning():
            try:
                return self._submit_learning_session_legacy(
                    session_id=session_id,
                    user_id=user_id,
                    answer=answer,
                    confidence=confidence,
                    response_time_seconds=response_time_seconds,
                    result_override=result_override,
                    error_type=error_type,
                    user_reasoning=user_reasoning,
                    now=now,
                )
            except (OperationalError, ProgrammingError):
                self.db.rollback()
                self._legacy_schema_available = False
        return self._submit_learning_session_opec(
            session_id=session_id,
            user_id=user_id,
            answer=answer,
            confidence=confidence,
            response_time_seconds=response_time_seconds,
            result_override=result_override,
            error_type=error_type,
            user_reasoning=user_reasoning,
            now=now,
        )

    def _submit_learning_session_legacy(
        self,
        *,
        session_id: str,
        user_id: int,
        answer: str,
        confidence: str,
        response_time_seconds: Optional[int],
        result_override: Optional[str],
        error_type: Optional[str],
        user_reasoning: Optional[str],
        now: datetime,
    ) -> SubmissionResult:
        session = self.db.query(LearningSession).filter_by(
            id=session_id, user_id=user_id, status="active"
        ).first()
        if session is None or not session.current_question_id:
            raise ValueError("No existe una sesión activa con pregunta pendiente")
        canonical, _active_opec, _eligible = self._validated_context(session, now)
        if session.status != "active" or canonical is None:
            self.db.commit()
            raise ValueError("La OPEC activa cambió; inicia una sesión nueva")
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

        canonical_event = record_opec_event(
            self.db,
            session_id=canonical.id,
            user_id=user_id,
            question_id=str(question.question_id),
            chosen_key=answer,
            confidence=confidence,
            time_sec=(
                int(response_time_seconds)
                if response_time_seconds is not None
                else None
            ),
            error_category=error_type,
            user_reasoning=user_reasoning,
            now=now,
        )

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
        self._set_session_current_question_id(session, next_question.question_id if next_question else None)
        self.db.commit()
        canonical_mastery = (
            self.db.query(OpecTopicState)
            .filter_by(
                user_id=user_id,
                competition_id=canonical.competition_id,
                user_opec_id=canonical.user_opec_id,
                topic_id=canonical_event.topic_id,
            )
            .first()
        )
        reported_mastery = (
            float(canonical_mastery.mastery_score)
            if canonical_mastery is not None
            else float(mastery.mastery_score)
        )
        reported_review = (
            canonical_mastery.next_review_at
            if canonical_mastery is not None
            else mastery.next_review_at
        )
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
            mastery_score=reported_mastery,
            next_review_at=reported_review,
        )

    def _submit_learning_session_opec(
        self,
        *,
        session_id: str,
        user_id: int,
        answer: str,
        confidence: str,
        response_time_seconds: Optional[int],
        result_override: Optional[str],
        error_type: Optional[str],
        user_reasoning: Optional[str],
        now: datetime,
    ) -> SubmissionResult:
        session = self.db.get(OpecLearningSession, session_id)
        if session is None or session.user_id != user_id:
            raise ValueError("No existe una sesión activa con pregunta pendiente")
        session, _active_opec, _eligible = self._validated_opec_context(session, now)
        if session.status != "active":
            self.db.commit()
            raise ValueError("La OPEC activa cambió; inicia una sesión nueva")
        current_id = self._session_current_question_id(session)
        if current_id is None:
            selected = self._select(session, now)
            if selected is None:
                raise ValueError("No existe una sesión activa con pregunta pendiente")
            current_id = str(selected.question_id)
            self._set_session_current_question_id(session, current_id)
            question = self.db.get(Question, current_id)
            if question is None:
                self.db.rollback()
                raise ValueError("La pregunta activa ya no existe")
        question = self.db.get(Question, current_id)
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

        canonical_event = record_opec_event(
            self.db,
            session_id=session.id,
            user_id=user_id,
            question_id=str(question.question_id),
            chosen_key=answer,
            confidence=confidence,
            time_sec=(
                int(response_time_seconds)
                if response_time_seconds is not None
                else None
            ),
            error_category=error_type,
            user_reasoning=user_reasoning,
            now=now,
        )

        next_question = self._select(session, now)
        self._set_session_current_question_id(session, next_question.question_id if next_question else None)
        self.db.commit()

        canonical_state = (
            self.db.query(OpecTopicState)
            .filter_by(
                user_id=user_id,
                competition_id=session.competition_id,
                user_opec_id=session.user_opec_id,
                topic_id=canonical_event.topic_id,
            )
            .first()
        )
        reported_mastery = float(canonical_state.mastery_score) if canonical_state is not None else 0.0
        reported_review = (
            canonical_state.next_review_at
            if canonical_state is not None
            else now
        )
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
            mastery_score=reported_mastery,
            next_review_at=reported_review,
        )

    def finish_session(
        self, session_id: str, user_id: int, *, now: Optional[datetime] = None
    ) -> LearningSession:
        now = now or utc_now()
        if self._legacy_schema_available_for_learning():
            try:
                return self._finish_learning_session_legacy(
                    session_id=session_id,
                    user_id=user_id,
                    now=now,
                )
            except (OperationalError, ProgrammingError):
                self.db.rollback()
                self._legacy_schema_available = False
        return self._finish_learning_session_opec(
            session_id=session_id,
            user_id=user_id,
            now=now,
        )

    def _finish_learning_session_legacy(
        self,
        session_id: str,
        user_id: int,
        now: datetime,
    ) -> LearningSession:
        session = self.db.query(LearningSession).filter_by(
            id=session_id, user_id=user_id
        ).first()
        if session is None or session.status != "active":
            raise ValueError("Sesión no encontrada")
        canonical, _active_opec, _eligible = self._validated_context(session, now)
        if session.status != "active" or canonical is None:
            self.db.commit()
            raise ValueError("La OPEC activa cambió; la sesión no puede finalizarse")
        finalize_opec_session(
            self.db,
            session_id=canonical.id,
            user_id=user_id,
            now=now,
            require_complete=False,
        )
        session.finished_at = session.finished_at or now
        session.actual_minutes = max(
            0, int((session.finished_at - session.started_at).total_seconds() // 60)
        )
        session.status = "completed"
        session.current_question_id = None
        self.db.commit()
        return session

    def _finish_learning_session_opec(
        self,
        session_id: str,
        user_id: int,
        now: datetime,
    ) -> LearningSession:
        session = self.db.get(OpecLearningSession, session_id)
        if session is None or session.user_id != user_id or session.status != "active":
            raise ValueError("Sesión no encontrada")
        session, _active_opec, _eligible = self._validated_opec_context(session, now)
        if session.status != "active":
            self.db.commit()
            raise ValueError("La OPEC activa cambió; la sesión no puede finalizarse")
        finalize_opec_session(
            self.db,
            session_id=session.id,
            user_id=user_id,
            now=now,
            require_complete=False,
        )
        self._set_session_current_question_id(session, None)
        coverage = session.coverage if isinstance(session.coverage, dict) else {}
        duration_minutes = max(
            0, int((now - session.started_at).total_seconds() // 60)
        )
        coverage["actual_minutes"] = duration_minutes
        session.coverage = coverage
        self.db.commit()
        return session

    def learning_profile(self, user_id: int, competition_id: Optional[int], now=None) -> dict:
        now = now or utc_now()
        try:
            active_opec = self._active_opec(user_id, competition_id)
            questions = self._questions(
                competition_id,
                user_id,
                user_opec=active_opec,
            )
        except (OperationalError, ProgrammingError):
            self.db.rollback()
            active_opec = None
            questions = []

        topic_metadata = {
            topic_id_for(question.track, question.competency, question.topic): question
            for question in questions
        }
        try:
            states = []
            if active_opec is not None:
                states = self._load_profile_states(user_id, competition_id, active_opec)
        except (OperationalError, ProgrammingError):
            self.db.rollback()
            states = []
        topics = [
            TutorTopicProfile(
                topic_id=row.topic_id,
                topic_label=row.topic_label,
                competency=(
                    topic_metadata[row.topic_id].competency
                    if row.topic_id in topic_metadata
                    else None
                ),
                track=(
                    topic_metadata[row.topic_id].track
                    if row.topic_id in topic_metadata
                    else None
                ),
                mastery_score=float(row.mastery_score or 0.0),
                attempts=int(
                    row.evidence_count
                    if hasattr(row, "evidence_count")
                    else row.attempts
                ),
                last_reviewed_at=(
                    row.last_event_at
                    if hasattr(row, "last_event_at")
                    else getattr(row, "last_reviewed_at", None)
                ),
                next_review_at=row.next_review_at,
            )
            for row in states
            if row.topic_id in topic_metadata
        ]
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

    def recent_evolution(
        self,
        user_id: int,
        competition_id: Optional[int],
        *,
        limit: int = 30,
    ) -> list[dict]:
        """Return canonical answer history for only the active OPEC."""
        active_opec = self._active_opec(user_id, competition_id)
        if active_opec is None:
            return []
        rows = (
            self.db.query(OpecLearningEvent)
            .join(OpecLearningSession)
            .filter(
                OpecLearningEvent.user_id == user_id,
                OpecLearningSession.competition_id == competition_id,
                OpecLearningSession.user_opec_id == active_opec.id,
                OpecLearningEvent.is_correct.is_not(None),
            )
            .order_by(OpecLearningEvent.created_at.desc())
            .limit(min(max(int(limit), 1), 100))
            .all()
        )
        return [
            {
                "created_at": row.created_at,
                "score": 100.0 if row.is_correct else 0.0,
            }
            for row in reversed(rows)
        ]
