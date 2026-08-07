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


class FakeGeminiModels:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            parsed=self.parsed,
            text=None,
            usage_metadata=SimpleNamespace(
                prompt_token_count=15,
                candidates_token_count=9,
            ),
        )


def test_gemini_dict_response_is_normalized_to_schema(monkeypatch):
    monkeypatch.delenv("MODEL_FAST", raising=False)
    models = FakeGeminiModels(evaluation().model_dump(mode="json"))
    router = ModelRouter(provider="gemini", client=SimpleNamespace(models=models))
    result = router.generate_structured(
        task_type="test",
        prompt="prompt",
        schema=EvaluationResult,
        profile=ModelProfile.FAST,
    )
    assert isinstance(result, EvaluationResult)
    assert result.result.value == "partial"


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


def test_router_uses_free_gemini_with_structured_output(monkeypatch):
    monkeypatch.delenv("MODEL_BALANCED", raising=False)
    models = FakeGeminiModels(evaluation())
    router = ModelRouter(
        provider="gemini",
        client=SimpleNamespace(models=models),
    )
    result = router.generate_structured(
        task_type="tutor_feedback",
        prompt="prompt",
        schema=EvaluationResult,
        profile=ModelProfile.BALANCED,
    )
    assert result.result.value == "partial"
    assert models.calls[0]["model"] == "gemini-3.6-flash"
    assert (
        models.calls[0]["config"].response_json_schema
        == EvaluationResult.model_json_schema()
    )


def test_router_auto_detects_existing_gemini_key(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    for name in ("MODEL_FAST", "MODEL_BALANCED", "MODEL_REASONING"):
        monkeypatch.delenv(name, raising=False)
    router = ModelRouter(client=SimpleNamespace(models=FakeGeminiModels(evaluation())))
    assert router.provider == "gemini"
    assert router.available is True
    assert router.model_for(ModelProfile.FAST) == "gemini-3.6-flash"


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
