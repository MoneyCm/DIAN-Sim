"""Router desacoplado con salida estructurada y telemetría segura."""

from __future__ import annotations

from enum import Enum
import os
import time
from typing import Optional, Type

from pydantic import BaseModel
from dotenv import load_dotenv

from core.ai.usage_policy import (
    AIUsageLimitError,
    AIUsagePolicy,
    DEFAULT_AI_USAGE_POLICY,
    assert_ai_usage_allowed,
)


load_dotenv()


def _setting(name: str) -> Optional[str]:
    """Lee configuración local o Streamlit Secrets sin exponerla."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


class AIUnavailable(RuntimeError):
    pass


class ModelProfile(str, Enum):
    FAST = "FAST"
    BALANCED = "BALANCED"
    REASONING = "REASONING"


class ModelRouter:
    def __init__(
        self,
        *,
        client=None,
        provider: Optional[str] = None,
        db_factory=None,
        usage_policy: AIUsagePolicy = DEFAULT_AI_USAGE_POLICY,
    ):
        configured_provider = provider or _setting("AI_PROVIDER") or _setting("LLM_PROVIDER")
        if not configured_provider:
            if _setting("GEMINI_API_KEY"):
                configured_provider = "gemini"
            elif _setting("OPENAI_API_KEY"):
                configured_provider = "openai"
        self.provider = (configured_provider or "none").lower()
        default_models = {
            "gemini": {
                ModelProfile.FAST: "gemini-2.5-flash",
                ModelProfile.BALANCED: "gemini-2.5-flash",
                ModelProfile.REASONING: "gemini-2.5-flash",
            },
            "openai": {
                ModelProfile.FAST: "gpt-5.6-luna",
                ModelProfile.BALANCED: "gpt-5.6-terra",
                ModelProfile.REASONING: "gpt-5.6-sol",
            },
        }.get(self.provider, {})
        self.models = {
            profile: _setting(f"MODEL_{profile.value}") or default_models.get(profile, "")
            for profile in ModelProfile
        }
        self.db_factory = db_factory
        self.usage_policy = usage_policy
        self.client = client
        if self.client is None and self.provider == "openai" and _setting("OPENAI_API_KEY"):
            from openai import OpenAI

            self.client = OpenAI(api_key=_setting("OPENAI_API_KEY"))
        elif self.client is None and self.provider == "gemini" and _setting("GEMINI_API_KEY"):
            from google import genai

            self.client = genai.Client(api_key=_setting("GEMINI_API_KEY"))

    @property
    def available(self) -> bool:
        return self.provider in {"openai", "gemini"} and self.client is not None

    def model_for(self, profile: ModelProfile) -> str:
        return self.models[ModelProfile(profile)]

    def _log(self, **values) -> None:
        if self.db_factory is None:
            return
        db = None
        try:
            from db.models import AICallLog

            db = self.db_factory()
            db.add(AICallLog(**values))
            db.commit()
        except Exception:
            if db is not None:
                db.rollback()
        finally:
            if db is not None:
                db.close()

    def _check_budget(self, *, user_id: Optional[int], prompt: str) -> None:
        if self.db_factory is None:
            assert_ai_usage_allowed(
                None,
                user_id=user_id,
                prompt=prompt,
                policy=self.usage_policy,
            )
            return
        db = self.db_factory()
        try:
            assert_ai_usage_allowed(
                db,
                user_id=user_id,
                prompt=prompt,
                policy=self.usage_policy,
            )
        finally:
            db.close()

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
            self._check_budget(user_id=user_id, prompt=prompt)
            if not self.available:
                raise AIUnavailable("Proveedor de IA no configurado")
            if self.provider == "openai":
                response = self.client.responses.parse(
                    model=model,
                    input=prompt,
                    text_format=schema,
                    reasoning={"effort": "low" if profile != ModelProfile.REASONING else "medium"},
                    max_output_tokens=self.usage_policy.max_output_tokens_per_call,
                )
                parsed = response.output_parsed
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "input_tokens", None)
                output_tokens = getattr(usage, "output_tokens", None)
            elif self.provider == "gemini":
                from google.genai import types

                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=schema.model_json_schema(),
                        max_output_tokens=self.usage_policy.max_output_tokens_per_call,
                    ),
                )
                parsed = getattr(response, "parsed", None)
                if parsed is None and getattr(response, "text", None):
                    parsed = schema.model_validate_json(response.text)
                usage = getattr(response, "usage_metadata", None)
                input_tokens = getattr(usage, "prompt_token_count", None)
                output_tokens = getattr(usage, "candidates_token_count", None)
            else:
                raise AIUnavailable(f"Proveedor no compatible: {self.provider}")
            if parsed is None:
                raise AIUnavailable("La IA no devolvió una salida estructurada")
            if not isinstance(parsed, schema):
                parsed = schema.model_validate(parsed)
            success = True
            return parsed
        except Exception as exc:
            error_code = type(exc).__name__
            if isinstance(exc, AIUnavailable):
                raise
            if isinstance(exc, AIUsageLimitError):
                raise AIUnavailable(str(exc)) from exc
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
