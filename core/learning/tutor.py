"""Tutor opcional: mejora el feedback, pero conserva el resultado del motor."""

from core.ai.model_router import AIUnavailable, ModelProfile, ModelRouter
from core.learning.schemas import EvaluationResult
from core.prompts.tutor.v1 import PROMPT_VERSION, build_feedback_prompt


class TutorService:
    def __init__(self, router: ModelRouter):
        self.router = router

    def explain(self, *, stem: str, answer: str, deterministic: EvaluationResult,
                rationale: str, confidence: str, user_id: int | None = None) -> EvaluationResult:
        if not self.router.available:
            return deterministic
        try:
            enriched = self.router.generate_structured(
                task_type="tutor_feedback",
                prompt=build_feedback_prompt(
                    stem=stem, answer=answer, result=deterministic.result.value,
                    rationale=rationale, confidence=confidence,
                ),
                schema=EvaluationResult,
                profile=ModelProfile.BALANCED,
                prompt_version=PROMPT_VERSION,
                user_id=user_id,
            )
            if enriched.result != deterministic.result:
                return deterministic
            enriched.score = deterministic.score
            enriched.needs_review = deterministic.needs_review
            return enriched
        except AIUnavailable:
            return deterministic
