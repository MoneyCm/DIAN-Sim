"""Deterministic exposure rules for OPEC-scoped training and measurement.

The module is deliberately persistence-agnostic.  Callers pass events already
filtered by user, competition and OPEC, preventing a global exposure count from
leaking across study contexts.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ExposureSnapshot:
    question_counts: Mapping[str, int] = field(default_factory=dict)
    case_counts: Mapping[str, int] = field(default_factory=dict)
    revision_counts: Mapping[str, int] = field(default_factory=dict)

    def question_count(self, question_id: object) -> int:
        return max(0, int(self.question_counts.get(str(question_id), 0)))

    def case_count(self, case_id: object) -> int:
        return max(0, int(self.case_counts.get(str(case_id), 0)))

    def revision_count(self, revision_id: object) -> int:
        return max(0, int(self.revision_counts.get(str(revision_id), 0)))


@dataclass(frozen=True)
class MeasurementSelection:
    blocks: tuple
    requested_count: int
    novel_available: int
    complete: bool
    reason: str


def exposure_snapshot(events: Iterable[object]) -> ExposureSnapshot:
    question_counts: Counter[str] = Counter()
    case_counts: Counter[str] = Counter()
    revision_counts: Counter[str] = Counter()
    for event in events or ():
        question_id = str(getattr(event, "question_id", "") or "").strip()
        case_id = str(getattr(event, "case_id", "") or "").strip()
        revision_id = str(getattr(event, "question_revision_id", "") or "").strip()
        if question_id:
            question_counts[question_id] += 1
        if case_id:
            case_counts[case_id] += 1
        if revision_id:
            revision_counts[revision_id] += 1
    return ExposureSnapshot(
        question_counts=dict(question_counts),
        case_counts=dict(case_counts),
        revision_counts=dict(revision_counts),
    )


def _base_case_id(block: object) -> str:
    questions = list(getattr(block, "questions", None) or ())
    case_ids = {
        str(getattr(question, "case_id", "") or "").strip()
        for question in questions
        if str(getattr(question, "case_id", "") or "").strip()
    }
    if len(case_ids) == 1:
        return next(iter(case_ids))
    return str(getattr(block, "id", "") or "").strip()


def block_is_novel(block: object, snapshot: ExposureSnapshot) -> bool:
    case_id = _base_case_id(block)
    if case_id and snapshot.case_count(case_id):
        return False
    questions = list(getattr(block, "questions", None) or ())
    return bool(questions) and all(
        snapshot.question_count(getattr(question, "question_id", "")) == 0
        for question in questions
    )


def _balanced(blocks: Sequence[object], target_count: int, preferred_topics=()) -> list:
    if target_count <= 0:
        return []
    preferred = {
        str(topic): index for index, topic in enumerate(preferred_topics or ())
    }
    grouped: dict[str, deque] = defaultdict(deque)
    ordered = sorted(
        blocks,
        key=lambda block: (
            preferred.get(
                str(getattr(block, "topic", "") or "General"), len(preferred)
            ),
            str(getattr(block, "topic", "") or "General"),
            _base_case_id(block),
            str(getattr(block, "id", "") or ""),
        ),
    )
    for block in ordered:
        topic = str(getattr(block, "topic", "") or "General")
        grouped[topic].append(block)
    topics = sorted(
        grouped,
        key=lambda topic: (preferred.get(topic, len(preferred)), topic),
    )
    selected = []
    while topics and len(selected) < target_count:
        next_topics = []
        for topic in topics:
            if len(selected) >= target_count:
                break
            selected.append(grouped[topic].popleft())
            if grouped[topic]:
                next_topics.append(topic)
        topics = next_topics
    return selected


def select_novel_measurement_blocks(
    blocks: Iterable[object],
    *,
    target_count: int,
    snapshot: ExposureSnapshot,
    preferred_topics=(),
) -> MeasurementSelection:
    """Select only unseen cases/questions for a strict measurement.

    Repetition is not used as a silent fallback.  A partial novel selection is
    returned with ``complete=False`` so the caller can explain the bank gap or
    decline to launch a supposedly comparable measurement.
    """
    target = max(0, int(target_count))
    novel = [block for block in blocks or () if block_is_novel(block, snapshot)]
    selected = _balanced(novel, min(target, len(novel)), preferred_topics)
    complete = len(selected) == target and target > 0
    if target <= 0:
        reason = "La configuración solicita cero casos."
    elif complete:
        reason = "La selección usa únicamente casos y preguntas no vistos en medición."
    else:
        reason = (
            f"Solo hay {len(novel)} caso(s) nuevos para una meta de {target}; "
            "el banco de medición debe ampliarse antes de una sesión comparable."
        )
    return MeasurementSelection(
        blocks=tuple(selected),
        requested_count=target,
        novel_available=len(novel),
        complete=complete,
        reason=reason,
    )
