"""Deterministic, exposure-aware builders for OPEC training modes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from core.learning.engine import editorial_question_difficulty
from core.opec_question_context import function_number_for_question


MODE_RECOMMENDED = "recommended"
MODE_TOPIC = "topic_short"
MODE_COMPETENCY = "competency"
MODE_FUNCTION = "function"
MODE_PARTIAL = "partial"
MODE_FULL = "full_training"
MODE_ERRORS = "error_transfer"
MODE_MAXIMUM = "maximum_demand"

VALID_MODES = frozenset(
    {
        MODE_RECOMMENDED,
        MODE_TOPIC,
        MODE_COMPETENCY,
        MODE_FUNCTION,
        MODE_PARTIAL,
        MODE_FULL,
        MODE_ERRORS,
        MODE_MAXIMUM,
    }
)
CASE_PRESERVING_MODES = frozenset({MODE_PARTIAL, MODE_FULL, MODE_MAXIMUM})
STRICT_COMPLETENESS_MODES = frozenset(
    {MODE_PARTIAL, MODE_FULL, MODE_ERRORS, MODE_MAXIMUM}
)


@dataclass(frozen=True)
class PracticeSelection:
    mode: str
    questions: tuple
    requested_count: int
    complete: bool
    reason: str
    feedback_enabled: bool
    aids_allowed: bool
    resumable: bool


def _question_id(question: object) -> str:
    return str(getattr(question, "question_id", "") or "").strip()


def _case_id(question: object) -> str:
    return str(getattr(question, "case_id", "") or "").strip()


def _exposure(question: object, counts: Mapping[str, int]) -> int:
    return max(0, int(counts.get(_question_id(question), 0)))


def _base_filter(
    questions: Iterable[object],
    *,
    mode: str,
    opec_number: object,
    exposure_counts: Mapping[str, int],
    max_exposures: int,
    topics: Sequence[str],
    competencies: Sequence[str],
    function_numbers: Sequence[int],
    error_question_ids: set[str],
    error_topic_ids: set[str],
) -> list:
    topic_filter = {str(item) for item in topics if str(item).strip()}
    competency_filter = {
        str(item) for item in competencies if str(item).strip()
    }
    function_filter = {int(item) for item in function_numbers}
    candidates = []
    for question in questions or ():
        question_id = _question_id(question)
        if not question_id or _exposure(question, exposure_counts) >= max_exposures:
            continue
        if str(getattr(question, "question_type", "SITUATIONAL")).upper() != "SITUATIONAL":
            continue
        if str(getattr(question, "track", "FUNCIONAL")).upper() != "FUNCIONAL":
            continue
        if topic_filter and str(getattr(question, "topic", "")) not in topic_filter:
            continue
        if competency_filter and str(getattr(question, "competency", "")) not in competency_filter:
            continue
        function_number = function_number_for_question(question, opec_number)
        if function_filter and function_number not in function_filter:
            continue
        if mode == MODE_ERRORS:
            if question_id in error_question_ids:
                continue
            topic_id = str(getattr(question, "topic", "") or "")
            function_token = f"F{function_number}" if function_number else ""
            if not error_topic_ids.intersection({topic_id, function_token}):
                continue
        if mode == MODE_MAXIMUM and editorial_question_difficulty(question) < 8:
            continue
        if mode in CASE_PRESERVING_MODES and not _case_id(question):
            continue
        candidates.append(question)
    return candidates


def _rank(question: object, exposure_counts: Mapping[str, int], mode: str):
    difficulty = editorial_question_difficulty(question)
    return (
        _exposure(question, exposure_counts),
        -difficulty if mode == MODE_MAXIMUM else difficulty,
        _case_id(question),
        _question_id(question),
    )


def _select_case_blocks(
    candidates: Sequence[object],
    *,
    requested_count: int,
    exposure_counts: Mapping[str, int],
    mode: str,
) -> list:
    grouped: dict[str, list] = defaultdict(list)
    for question in candidates:
        grouped[_case_id(question)].append(question)
    ordered_groups = []
    for case_id, group in grouped.items():
        group.sort(key=lambda question: _rank(question, exposure_counts, mode))
        if mode == MODE_MAXIMUM and any(
            editorial_question_difficulty(question) < 8 for question in group
        ):
            continue
        ordered_groups.append(
            (
                max(_exposure(question, exposure_counts) for question in group),
                -sum(editorial_question_difficulty(question) for question in group)
                if mode == MODE_MAXIMUM
                else min(editorial_question_difficulty(question) for question in group),
                case_id,
                group[:3],
            )
        )
    selected = []
    for _, _, _, group in sorted(ordered_groups):
        if len(selected) + len(group) > requested_count:
            continue
        selected.extend(group)
        if len(selected) == requested_count:
            break
    return selected


def select_practice_questions(
    questions: Iterable[object],
    *,
    mode: str,
    requested_count: int,
    opec_number: object,
    exposure_counts: Mapping[str, int] | None = None,
    max_exposures: int = 3,
    topics: Sequence[str] = (),
    competencies: Sequence[str] = (),
    function_numbers: Sequence[int] = (),
    error_question_ids: Iterable[str] = (),
    error_topic_ids: Iterable[str] = (),
) -> PracticeSelection:
    if mode not in VALID_MODES:
        raise ValueError("Modo de práctica no válido.")
    target = max(1, int(requested_count))
    if max_exposures < 1:
        raise ValueError("El límite de exposición debe ser positivo.")
    exposure_counts = {
        str(key): max(0, int(value))
        for key, value in (exposure_counts or {}).items()
    }
    candidates = _base_filter(
        questions,
        mode=mode,
        opec_number=opec_number,
        exposure_counts=exposure_counts,
        max_exposures=max_exposures,
        topics=topics,
        competencies=competencies,
        function_numbers=function_numbers,
        error_question_ids={str(item) for item in error_question_ids},
        error_topic_ids={str(item) for item in error_topic_ids},
    )
    if mode in CASE_PRESERVING_MODES:
        selected = _select_case_blocks(
            candidates,
            requested_count=target,
            exposure_counts=exposure_counts,
            mode=mode,
        )
    else:
        selected = sorted(
            candidates, key=lambda question: _rank(question, exposure_counts, mode)
        )[:target]

    complete = len(selected) == target
    if complete:
        reason = (
            f"Se seleccionaron {target} preguntas dentro del límite de exposición."
        )
    else:
        reason = (
            f"Solo hay {len(selected)} pregunta(s) elegibles de {target}; revisa cobertura, "
            "dificultad, fuentes o límite de exposición."
        )
    return PracticeSelection(
        mode=mode,
        questions=tuple(selected),
        requested_count=target,
        complete=complete,
        reason=reason,
        feedback_enabled=True,
        aids_allowed=mode != MODE_MAXIMUM,
        resumable=True,
    )
