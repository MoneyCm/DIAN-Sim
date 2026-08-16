"""Pure editorial-difficulty policy for adaptive learning.

The canonical scale is 1–10. Legacy 1–3 values are converted only when the
caller explicitly declares that source scale; this avoids reinterpreting an
already-normalized value on subsequent runs.

Response time and self-reported confidence are deliberately excluded from the
target-difficulty calculation. They can raise review priority, but never lower
the learner's demonstrated score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional


EDITORIAL_SCALE_VERSION = "editorial-difficulty-1-10-v1"
LEGACY_TO_EDITORIAL = {1: 2, 2: 5, 3: 8}


class EditorialDifficulty(int):
    """An integer tagged as already normalized to the editorial scale.

    The marker survives ordinary integer comparison/serialization and makes a
    repeated legacy conversion idempotent within the normalization pipeline.
    """

    scale_version = EDITORIAL_SCALE_VERSION

    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10:
            raise ValueError("La dificultad editorial debe ser un entero entre 1 y 10.")
        return int.__new__(cls, value)


@dataclass(frozen=True)
class DifficultyRubric:
    score: int
    label: str
    description: str


DIFFICULTY_RUBRIC = (
    DifficultyRubric(1, "Reconocimiento", "Identifica conceptos y señales esenciales."),
    DifficultyRubric(2, "Comprensión", "Explica la regla básica en un contexto directo."),
    DifficultyRubric(3, "Aplicación guiada", "Aplica una regla con datos y ruta evidentes."),
    DifficultyRubric(4, "Aplicación autónoma", "Selecciona el procedimiento sin guía explícita."),
    DifficultyRubric(5, "Integración", "Relaciona varias reglas o controles del mismo tema."),
    DifficultyRubric(6, "Análisis", "Distingue evidencia relevante y consecuencias operativas."),
    DifficultyRubric(7, "Decisión compleja", "Prioriza actuaciones frente a restricciones concurrentes."),
    DifficultyRubric(8, "Juicio avanzado", "Resuelve ambigüedad normativa o procedimental sustentada."),
    DifficultyRubric(9, "Transferencia", "Transfiere el criterio a un escenario novedoso."),
    DifficultyRubric(10, "Dominio robusto", "Integra, transfiere y justifica bajo alta complejidad."),
)


@dataclass(frozen=True)
class DifficultyPolicy:
    version: str = EDITORIAL_SCALE_VERSION
    min_total_attempts: int = 8
    min_new_attempts: int = 4
    min_delayed_retention_attempts: int = 3
    min_measurement_attempts: int = 3
    promotion_new_accuracy: float = 0.75
    promotion_retention_accuracy: float = 0.70
    promotion_measurement_accuracy: float = 0.70
    weak_accuracy: float = 0.55
    very_weak_accuracy: float = 0.40
    max_lapses_for_promotion: int = 0
    lapses_per_penalty: int = 2
    max_promotion_step: int = 1

    def __post_init__(self) -> None:
        if not str(self.version).strip():
            raise ValueError("La política de dificultad debe declarar una versión.")
        integer_fields = (
            self.min_total_attempts,
            self.min_new_attempts,
            self.min_delayed_retention_attempts,
            self.min_measurement_attempts,
            self.max_lapses_for_promotion,
            self.lapses_per_penalty,
            self.max_promotion_step,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in integer_fields
        ):
            raise ValueError("Los mínimos y límites de la política deben ser enteros.")
        if any(value < 0 for value in integer_fields):
            raise ValueError("Los mínimos y límites de la política no pueden ser negativos.")
        if self.lapses_per_penalty < 1 or self.max_promotion_step < 1:
            raise ValueError("Los pasos de lapsos y promoción deben ser al menos uno.")
        ratios = (
            self.promotion_new_accuracy,
            self.promotion_retention_accuracy,
            self.promotion_measurement_accuracy,
            self.weak_accuracy,
            self.very_weak_accuracy,
        )
        if any(not 0.0 <= value <= 1.0 for value in ratios):
            raise ValueError("Los umbrales de precisión deben estar entre 0 y 1.")
        if self.very_weak_accuracy > self.weak_accuracy:
            raise ValueError("El umbral muy débil no puede superar el umbral débil.")


DEFAULT_DIFFICULTY_POLICY = DifficultyPolicy()


@dataclass(frozen=True)
class TopicDifficultyEvidence:
    mastery: float
    current_difficulty: int
    total_attempts: int
    new_attempts: int
    new_correct: int
    delayed_retention_attempts: int
    delayed_retention_correct: int
    measurement_attempts: int
    measurement_correct: int
    lapses: int = 0
    slow_response_ratio: float = 0.0
    low_confidence_ratio: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(float(self.mastery)) or not 0.0 <= float(self.mastery) <= 100.0:
            raise ValueError("mastery debe estar entre 0 y 100.")
        _validate_editorial_score(self.current_difficulty)
        counts = (
            self.total_attempts,
            self.new_attempts,
            self.new_correct,
            self.delayed_retention_attempts,
            self.delayed_retention_correct,
            self.measurement_attempts,
            self.measurement_correct,
            self.lapses,
        )
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
            raise ValueError("Los conteos de evidencia deben ser enteros no negativos.")
        if self.new_correct > self.new_attempts:
            raise ValueError("new_correct no puede superar new_attempts.")
        if self.delayed_retention_correct > self.delayed_retention_attempts:
            raise ValueError(
                "delayed_retention_correct no puede superar delayed_retention_attempts."
            )
        if self.measurement_correct > self.measurement_attempts:
            raise ValueError("measurement_correct no puede superar measurement_attempts.")
        for name, ratio in (
            ("slow_response_ratio", self.slow_response_ratio),
            ("low_confidence_ratio", self.low_confidence_ratio),
        ):
            if not math.isfinite(float(ratio)) or not 0.0 <= float(ratio) <= 1.0:
                raise ValueError(f"{name} debe estar entre 0 y 1.")

    @property
    def new_accuracy(self) -> Optional[float]:
        return _accuracy(self.new_correct, self.new_attempts)

    @property
    def delayed_retention_accuracy(self) -> Optional[float]:
        return _accuracy(
            self.delayed_retention_correct,
            self.delayed_retention_attempts,
        )

    @property
    def measurement_accuracy(self) -> Optional[float]:
        return _accuracy(self.measurement_correct, self.measurement_attempts)


@dataclass(frozen=True)
class DifficultyDecision:
    policy_version: str
    target: int
    mastery_target: int
    evidence_sufficient: bool
    promotion_eligible: bool
    priority: float
    reasons: tuple[str, ...]

    @property
    def rubric(self) -> DifficultyRubric:
        return difficulty_rubric(self.target)


def _validate_editorial_score(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10:
        raise ValueError("La dificultad editorial debe ser un entero entre 1 y 10.")
    return value


def normalize_difficulty(
    value: int | EditorialDifficulty,
    *,
    source_scale: Literal["editorial", "legacy"] = "editorial",
) -> EditorialDifficulty:
    """Normalize a score without guessing its source scale.

    ``normalize_difficulty(legacy, source_scale="legacy")`` performs the one-time
    mapping. Passing its result through the default editorial normalization is
    idempotent.
    """

    if isinstance(value, EditorialDifficulty):
        return value
    if source_scale == "editorial":
        return EditorialDifficulty(_validate_editorial_score(value))
    if source_scale == "legacy":
        if not isinstance(value, int) or isinstance(value, bool) or value not in LEGACY_TO_EDITORIAL:
            raise ValueError("La dificultad legacy debe ser 1, 2 o 3.")
        return EditorialDifficulty(LEGACY_TO_EDITORIAL[value])
    raise ValueError("Escala de dificultad desconocida.")


def legacy_difficulty_to_editorial(
    value: int | EditorialDifficulty,
) -> EditorialDifficulty:
    return normalize_difficulty(value, source_scale="legacy")


def difficulty_rubric(score: int) -> DifficultyRubric:
    return DIFFICULTY_RUBRIC[_validate_editorial_score(score) - 1]


def difficulty_label(score: int) -> str:
    return difficulty_rubric(score).label


def mastery_difficulty(mastery: float) -> int:
    """Map mastery 0–100 monotonically to the editorial 1–10 scale."""

    numeric = float(mastery)
    if not math.isfinite(numeric) or not 0.0 <= numeric <= 100.0:
        raise ValueError("mastery debe estar entre 0 y 100.")
    return min(10, int(numeric // 10) + 1)


def _accuracy(correct: int, attempts: int) -> Optional[float]:
    return correct / attempts if attempts else None


def _weakness_penalty(accuracy: Optional[float], policy: DifficultyPolicy) -> int:
    if accuracy is None or accuracy >= policy.weak_accuracy:
        return 0
    return 2 if accuracy < policy.very_weak_accuracy else 1


def _priority_score(evidence: TopicDifficultyEvidence) -> float:
    """Prioritize weakness and friction without altering demonstrated mastery."""

    accuracies = tuple(
        value
        for value in (
            evidence.new_accuracy,
            evidence.delayed_retention_accuracy,
            evidence.measurement_accuracy,
        )
        if value is not None
    )
    observed_gap = (
        sum(1.0 - value for value in accuracies) / len(accuracies)
        if accuracies
        else 1.0
    )
    score = (
        0.35 * (1.0 - evidence.mastery / 100.0)
        + 0.25 * observed_gap
        + 0.15 * min(evidence.lapses / 4.0, 1.0)
        + 0.125 * evidence.slow_response_ratio
        + 0.125 * evidence.low_confidence_ratio
    )
    return round(min(max(score * 100.0, 0.0), 100.0), 2)


def target_difficulty(
    evidence: TopicDifficultyEvidence,
    policy: DifficultyPolicy = DEFAULT_DIFFICULTY_POLICY,
) -> DifficultyDecision:
    """Return a stable, evidence-gated difficulty target for one topic."""

    mastery_target = mastery_difficulty(evidence.mastery)
    new_accuracy = evidence.new_accuracy
    retention_accuracy = evidence.delayed_retention_accuracy
    measurement_accuracy = evidence.measurement_accuracy

    evidence_sufficient = (
        evidence.total_attempts >= policy.min_total_attempts
        and evidence.new_attempts >= policy.min_new_attempts
        and evidence.delayed_retention_attempts
        >= policy.min_delayed_retention_attempts
        and evidence.measurement_attempts >= policy.min_measurement_attempts
    )
    promotion_eligible = (
        evidence_sufficient
        and new_accuracy is not None
        and new_accuracy >= policy.promotion_new_accuracy
        and retention_accuracy is not None
        and retention_accuracy >= policy.promotion_retention_accuracy
        and measurement_accuracy is not None
        and measurement_accuracy >= policy.promotion_measurement_accuracy
        and evidence.lapses <= policy.max_lapses_for_promotion
    )

    penalties = (
        _weakness_penalty(new_accuracy, policy)
        + _weakness_penalty(retention_accuracy, policy)
        + _weakness_penalty(measurement_accuracy, policy)
    )
    lapse_penalty = evidence.lapses // policy.lapses_per_penalty
    proposed = max(1, mastery_target - penalties - lapse_penalty)
    reasons: list[str] = []

    weak_signals = tuple(
        (name, accuracy)
        for name, accuracy in (
            ("preguntas nuevas", new_accuracy),
            ("retención diferida", retention_accuracy),
            ("measurement", measurement_accuracy),
        )
        if accuracy is not None and accuracy < policy.weak_accuracy
    )
    if weak_signals:
        proposed = min(proposed, max(1, evidence.current_difficulty - 1))
        reasons.extend(f"precisión débil en {name}" for name, _ in weak_signals)
    if lapse_penalty:
        proposed = min(
            proposed,
            max(1, evidence.current_difficulty - lapse_penalty),
        )
        reasons.append(f"{evidence.lapses} lapsos recientes")

    if proposed > evidence.current_difficulty:
        if not promotion_eligible:
            proposed = evidence.current_difficulty
            reasons.append("ascenso bloqueado por evidencia insuficiente o no robusta")
        else:
            proposed = min(
                proposed,
                evidence.current_difficulty + policy.max_promotion_step,
            )
            reasons.append("ascenso respaldado por evidencia nueva, diferida y measurement")
    elif proposed < evidence.current_difficulty:
        reasons.append("objetivo reducido por desempeño observado, no por tiempo o confianza")
    else:
        reasons.append("mantener dificultad actual")

    if evidence.slow_response_ratio or evidence.low_confidence_ratio:
        reasons.append("tiempo/confianza aumentan prioridad sin reducir dificultad")

    return DifficultyDecision(
        policy_version=policy.version,
        target=_validate_editorial_score(proposed),
        mastery_target=mastery_target,
        evidence_sufficient=evidence_sufficient,
        promotion_eligible=promotion_eligible,
        priority=_priority_score(evidence),
        reasons=tuple(dict.fromkeys(reasons)),
    )
