"""Router desacoplado con salida estructurada y telemetría segura."""

from __future__ import annotations

from enum import Enum
import os
import time
from typing import Optional, Type

from pydantic import BaseModel


class AIUnavailable(RuntimeError):
    pass


class ModelProfile(str, Enum):
    FAST = "FAST"
    BALANCED = "BALANCED"
    REASONING = "REASONING"


class ModelRouter:
    def __init__(self, *, client=None, provider: Optional[str] = None, db_factory=None):
        self.provider = (provider or os.getenv("AI_PROVIDER") or os.getenv("LLM_PROVIDER") or "none").lower()
        self.models = {
            ModelProfile.FAST: os.getenv("MODEL_FAST", "gpt-5.6-luna"),
            ModelProfile.BALANCED: os.getenv("MODEL_BALANCED", "gpt-5.6-terra"),
            ModelProfile.REASONING: os.getenv("MODEL_REASONING", "gpt-5.6-sol"),
        }
        self.db_factory = db_factory
        self.client = client
        if self.client is None and self.provider == "openai" and os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI

            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @property
    def available(self) -> bool:
        return self.provider == "openai" and self.client is not None

    def model_for(self, profile: ModelProfile) -> str:
        return self.models[ModelProfile(profile)]

    def _log(self, **values) -> None:
        if self.db_factory is None:
            return
        try:
            from db.models import AICallLog

            db = self.db_factory()
            db.add(AICallLog(**values))
            db.commit()
            db.close()
        except Exception:
            pass

    def generate_structured(
        self,
        *,
        task_type: str,
        prompt: str,
        schema: Type[BaseModel],
        profile: ModelProfile = ModelProfile.BALANCED,
        prompt_version: str = "v1",
        user_id: Optional[int] = None,
    ) -> BaseModel:
        model = self.model_for(profile)
        started = time.perf_counter()
        success = False
        input_tokens = output_tokens = None
        error_code = None
        try:
            if not self.available:
                raise AIUnavailable("Proveedor de IA no configurado")
            response = self.client.responses.parse(
                model=model,
                input=prompt,
                text_format=schema,
                reasoning={"effort": "low" if profile != ModelProfile.REASONING else "medium"},
            )
            parsed = response.output_parsed
            if parsed is None:
                raise AIUnavailable("La IA no devolvió una salida estructurada")
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "input_tokens", None)
            output_tokens = getattr(usage, "output_tokens", None)
            success = True
            return parsed
        except Exception as exc:
            error_code = type(exc).__name__
            if isinstance(exc, AIUnavailable):
                raise
            raise AIUnavailable("La IA no está disponible; se aplicará el modo determinístico") from exc
        finally:
            self._log(
                user_id=user_id,
                provider=self.provider,
                model=model,
                task_type=task_type,
                prompt_version=prompt_version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=int((time.perf_counter() - started) * 1000),
                success=success,
                error_code=error_code,
            )
