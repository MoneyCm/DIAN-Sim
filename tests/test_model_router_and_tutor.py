from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.ai.model_router import AIUnavailable, ModelProfile, ModelRouter
from core.learning.schemas import EvaluationResult
from core.learning.tutor import TutorService
from db.models import AICallLog, Base


def evaluation(**overrides):
    values = {
        "result": "partial",
        "score": 0.6,
        "error_type": "application",
        "feedback": "Aplica el criterio al caso concreto.",
        "needs_review": True,
    }
    values.update(overrides)
    return EvaluationResult(**values)


class FakeResponses:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_parsed=self.parsed,
            usage=SimpleNamespace(input_tokens=12, output_tokens=8),
        )


def test_router_uses_configured_profile_and_structured_schema(monkeypatch):
    monkeypatch.setenv("MODEL_BALANCED", "verified-balanced-model")
    responses = FakeResponses(evaluation())
    router = ModelRouter(
        provider="openai", client=SimpleNamespace(responses=responses)
    )
    result = router.generate_structured(
        task_type="test",
        prompt="prompt",
        schema=EvaluationResult,
        profile=ModelProfile.BALANCED,
    )
    assert result.result.value == "partial"
    assert responses.calls[0]["model"] == "verified-balanced-model"
    assert responses.calls[0]["text_format"] is EvaluationResult


def test_router_fails_cleanly_without_provider():
    router = ModelRouter(provider="none")
    with pytest.raises(AIUnavailable):
        router.generate_structured(
            task_type="test", prompt="prompt", schema=EvaluationResult
        )


def test_tutor_falls_back_when_ai_is_unavailable():
    deterministic = evaluation(result="incorrect", score=0, error_type="distractor")
    result = TutorService(ModelRouter(provider="none")).explain(
        stem="Pregunta",
        answer="B",
        deterministic=deterministic,
        rationale="Fundamento",
        confidence="high",
    )
    assert result == deterministic


def test_router_logs_observability_without_prompt_content():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    responses = FakeResponses(evaluation())
    router = ModelRouter(
        provider="openai",
        client=SimpleNamespace(responses=responses),
        db_factory=session_factory,
    )
    router.generate_structured(
        task_type="evaluation",
        prompt="sensitive prompt not persisted",
        schema=EvaluationResult,
        profile=ModelProfile.FAST,
        prompt_version="evaluator-v1",
    )
    db = session_factory()
    row = db.query(AICallLog).one()
    assert row.success is True
    assert row.input_tokens == 12
    assert row.output_tokens == 8
    assert row.prompt_version == "evaluator-v1"
    assert not hasattr(row, "prompt")
    db.close()


def test_structured_schema_rejects_unknown_fields_and_bad_score():
    with pytest.raises(ValidationError):
        evaluation(score=2, unexpected="value")
