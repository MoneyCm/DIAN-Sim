"""Contratos estrictos entre interfaz, tutor, motor e IA."""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LearningResult(str, Enum):
    correct = "correct"
    partial = "partial"
    incorrect = "incorrect"


class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ErrorType(str, Enum):
    knowledge = "knowledge"
    interpretation = "interpretation"
    application = "application"
    normative_confusion = "normative_confusion"
    reading = "reading"
    distractor = "distractor"
    reasoning = "reasoning"
    memory = "memory"
    overconfidence = "overconfidence"


class EvaluationResult(StrictSchema):
    result: LearningResult
    score: float = Field(ge=0.0, le=1.0)
    error_type: Optional[ErrorType] = None
    feedback: str = Field(min_length=1, max_length=1200)
    needs_review: bool


class TutorDecision(StrictSchema):
    action: Literal["ask_question", "explain_gap", "finish_session"]
    topic_id: Optional[str] = None
    reason: str = Field(min_length=1, max_length=500)
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class QuestionView(StrictSchema):
    question_id: str
    stem: str
    options: dict[str, str]
    topic: str
    competency: str
    difficulty: int


class SessionView(StrictSchema):
    session_id: str
    status: str
    target_minutes: int
    started_at: datetime
    question: Optional[QuestionView] = None


class SubmissionResult(StrictSchema):
    evaluation: EvaluationResult
    next_question: Optional[QuestionView] = None
    mastery_score: float = Field(ge=0.0, le=100.0)
    next_review_at: datetime
