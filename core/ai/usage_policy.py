"""Provider-neutral, persistent safety limits for paid AI operations.

The policy uses the existing ``ai_call_logs`` table and never stores prompts or
keys.  Token limits are a cost proxy; exact currency estimates would be unsafe
without a versioned price catalogue for every provider/model.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import math
import os
from typing import Optional

from sqlalchemy import func


class AIUsageLimitError(RuntimeError):
    """A request is too large or the configured usage budget is exhausted."""


def _bounded_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


@dataclass(frozen=True)
class AIUsagePolicy:
    max_prompt_chars: int = 120_000
    max_calls_per_job: int = 25
    max_calls_per_user_day: int = 80
    max_calls_global_day: int = 1_000
    max_input_tokens_per_user_day: int = 300_000
    max_output_tokens_per_user_day: int = 100_000
    max_output_tokens_per_call: int = 4_096

    @classmethod
    def from_environment(cls) -> "AIUsagePolicy":
        return cls(
            max_prompt_chars=_bounded_env(
                "AI_MAX_PROMPT_CHARS", 120_000, minimum=2_000, maximum=250_000
            ),
            max_calls_per_job=_bounded_env(
                "AI_MAX_CALLS_PER_JOB", 25, minimum=1, maximum=100
            ),
            max_calls_per_user_day=_bounded_env(
                "AI_MAX_CALLS_PER_USER_DAY", 80, minimum=1, maximum=500
            ),
            max_calls_global_day=_bounded_env(
                "AI_MAX_CALLS_GLOBAL_DAY", 1_000, minimum=10, maximum=10_000
            ),
            max_input_tokens_per_user_day=_bounded_env(
                "AI_MAX_INPUT_TOKENS_PER_USER_DAY",
                300_000,
                minimum=10_000,
                maximum=2_000_000,
            ),
            max_output_tokens_per_user_day=_bounded_env(
                "AI_MAX_OUTPUT_TOKENS_PER_USER_DAY",
                100_000,
                minimum=5_000,
                maximum=500_000,
            ),
            max_output_tokens_per_call=_bounded_env(
                "AI_MAX_OUTPUT_TOKENS_PER_CALL", 4_096, minimum=256, maximum=16_384
            ),
        )


DEFAULT_AI_USAGE_POLICY = AIUsagePolicy.from_environment()


def estimate_tokens(text_or_chars: str | int | None) -> int:
    """Conservative provider-independent estimate (roughly four chars/token)."""
    if isinstance(text_or_chars, int):
        char_count = max(text_or_chars, 0)
    else:
        char_count = len(str(text_or_chars or ""))
    return math.ceil(char_count / 4) if char_count else 0


def _utc_day_start(now: Optional[dt.datetime] = None) -> dt.datetime:
    current = now or dt.datetime.now(dt.UTC)
    if current.tzinfo is not None:
        current = current.astimezone(dt.UTC).replace(tzinfo=None)
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


def assert_ai_usage_allowed(
    db,
    *,
    user_id: Optional[int],
    prompt: str,
    planned_calls: int = 1,
    policy: AIUsagePolicy = DEFAULT_AI_USAGE_POLICY,
    now: Optional[dt.datetime] = None,
) -> None:
    """Fail closed before a provider call when size or daily budgets are exceeded."""
    if not isinstance(prompt, str):
        raise AIUsageLimitError("La solicitud enviada a la IA no es válida.")
    if len(prompt) > policy.max_prompt_chars:
        raise AIUsageLimitError(
            f"La fuente supera el límite de {policy.max_prompt_chars:,} caracteres por solicitud."
        )
    if planned_calls < 1 or planned_calls > policy.max_calls_per_job:
        raise AIUsageLimitError(
            f"El lote supera el máximo seguro de {policy.max_calls_per_job} llamadas."
        )
    if db is None:
        return

    from db.models import AICallLog

    day_start = _utc_day_start(now)
    global_calls = int(
        db.query(func.count(AICallLog.id))
        .filter(AICallLog.created_at >= day_start)
        .scalar()
        or 0
    )
    if global_calls + planned_calls > policy.max_calls_global_day:
        raise AIUsageLimitError(
            "La cuota global diaria de IA está agotada; inténtalo después del próximo reinicio diario."
        )

    if user_id is None:
        return
    user_query = db.query(AICallLog).filter(
        AICallLog.user_id == user_id,
        AICallLog.created_at >= day_start,
    )
    user_calls = int(user_query.with_entities(func.count(AICallLog.id)).scalar() or 0)
    if user_calls + planned_calls > policy.max_calls_per_user_day:
        raise AIUsageLimitError(
            "Alcanzaste la cuota diaria de IA. Las funciones determinísticas siguen disponibles."
        )

    input_tokens, output_tokens = user_query.with_entities(
        func.coalesce(func.sum(AICallLog.input_tokens), 0),
        func.coalesce(func.sum(AICallLog.output_tokens), 0),
    ).one()
    projected_input = int(input_tokens or 0) + estimate_tokens(prompt) * planned_calls
    if projected_input > policy.max_input_tokens_per_user_day:
        raise AIUsageLimitError(
            "La solicitud excede el presupuesto diario de texto para IA. Reduce el documento o inténtalo mañana."
        )
    if int(output_tokens or 0) >= policy.max_output_tokens_per_user_day:
        raise AIUsageLimitError(
            "Alcanzaste el presupuesto diario de respuestas de IA."
        )


def _safe_label(value: object, *, fallback: str, max_length: int) -> str:
    text = str(value or fallback).strip() or fallback
    return text[:max_length]


def record_ai_calls(
    session_factory,
    *,
    user_id: Optional[int],
    provider: str,
    model: str,
    task_type: str,
    prompt_version: str,
    call_count: int,
    success: bool,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    latency_ms: int = 0,
    error_code: Optional[str] = None,
) -> None:
    """Record only metadata, distributing aggregate tokens over call rows."""
    if session_factory is None or call_count < 1:
        return
    from db.models import AICallLog

    db = session_factory()
    try:
        input_each = math.ceil(max(input_tokens or 0, 0) / call_count) or None
        output_each = math.ceil(max(output_tokens or 0, 0) / call_count) or None
        latency_each = max(int(latency_ms / call_count), 0)
        for _ in range(call_count):
            db.add(
                AICallLog(
                    user_id=user_id,
                    provider=_safe_label(provider, fallback="unknown", max_length=30),
                    model=_safe_label(model, fallback="unknown", max_length=100),
                    task_type=_safe_label(task_type, fallback="unspecified", max_length=50),
                    prompt_version=_safe_label(
                        prompt_version, fallback="v1", max_length=30
                    ),
                    input_tokens=input_each,
                    output_tokens=output_each,
                    latency_ms=latency_each,
                    success=bool(success),
                    error_code=(
                        _safe_label(error_code, fallback="Error", max_length=100)
                        if error_code
                        else None
                    ),
                )
            )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@dataclass
class AIUsageReservation:
    session_factory: object
    user_id: Optional[int]
    provider: str
    model: str
    task_type: str
    prompt_version: str
    planned_calls: int
    estimated_input_tokens: int
    _finished: bool = False

    def finish(
        self,
        *,
        success: bool,
        output_text: str = "",
        latency_ms: int = 0,
        completed_calls: Optional[int] = None,
        error: Optional[BaseException] = None,
    ) -> None:
        if self._finished:
            return
        self._finished = True
        calls = completed_calls if completed_calls is not None else (
            self.planned_calls if success else 1
        )
        calls = max(1, min(int(calls), self.planned_calls))
        record_ai_calls(
            self.session_factory,
            user_id=self.user_id,
            provider=self.provider,
            model=self.model,
            task_type=self.task_type,
            prompt_version=self.prompt_version,
            call_count=calls,
            success=success,
            input_tokens=self.estimated_input_tokens,
            output_tokens=estimate_tokens(output_text),
            latency_ms=latency_ms,
            error_code=type(error).__name__ if error else None,
        )


def reserve_ai_usage(
    session_factory,
    *,
    user_id: Optional[int],
    provider: str,
    model: str,
    task_type: str,
    prompt: str,
    planned_calls: int = 1,
    prompt_version: str = "v1",
    policy: AIUsagePolicy = DEFAULT_AI_USAGE_POLICY,
) -> AIUsageReservation:
    db = session_factory() if session_factory is not None else None
    try:
        assert_ai_usage_allowed(
            db,
            user_id=user_id,
            prompt=prompt,
            planned_calls=planned_calls,
            policy=policy,
        )
    finally:
        if db is not None:
            db.close()
    return AIUsageReservation(
        session_factory=session_factory,
        user_id=user_id,
        provider=provider,
        model=model,
        task_type=task_type,
        prompt_version=prompt_version,
        planned_calls=planned_calls,
        estimated_input_tokens=estimate_tokens(prompt) * planned_calls,
    )
