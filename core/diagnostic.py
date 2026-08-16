"""Pure, conservative construction of a nine-function diagnostic.

The selector accepts plain dataclasses and has no database or UI dependency.
It returns a partial selection plus explicit gaps when the trusted bank cannot
cover the policy; a partial result is never labelled as a valid diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


DIAGNOSTIC_POLICY_VERSION = "nine-function-diagnostic-v1"
OPEC_FUNCTIONS = tuple(range(1, 10))
VALID_PARTITIONS = frozenset({"training", "measurement"})


@dataclass(frozen=True)
class DiagnosticCandidate:
    question_id: str
    case_id: Optional[str]
    function_number: int
    revision_id: Optional[str]
    trusted: bool
    bank_partition: str
    question_type: str
    track: str = "FUNCIONAL"


@dataclass(frozen=True)
class DiagnosticPolicy:
    version: str = DIAGNOSTIC_POLICY_VERSION
    items_per_function: int = 1
    allowed_partitions: tuple[str, ...] = ("measurement", "training")
    partition_preference: tuple[str, ...] = ("measurement", "training")
    require_trusted: bool = True
    max_candidates_per_function: int = 50
    max_search_nodes: int = 50_000

    def __post_init__(self) -> None:
        if not str(self.version).strip():
            raise ValueError("La política diagnóstica debe declarar una versión.")
        if not isinstance(self.items_per_function, int) or isinstance(
            self.items_per_function, bool
        ) or self.items_per_function < 1:
            raise ValueError("items_per_function debe ser un entero positivo.")
        allowed = tuple(dict.fromkeys(self.allowed_partitions))
        preference = tuple(dict.fromkeys(self.partition_preference))
        if allowed != self.allowed_partitions or preference != self.partition_preference:
            raise ValueError("Las listas de particiones no pueden contener duplicados.")
        if not allowed or any(item not in VALID_PARTITIONS for item in allowed):
            raise ValueError("Las particiones permitidas deben ser training/measurement.")
        if set(preference) != set(allowed):
            raise ValueError(
                "partition_preference debe contener exactamente las particiones permitidas."
            )
        if (
            not isinstance(self.max_candidates_per_function, int)
            or isinstance(self.max_candidates_per_function, bool)
            or not isinstance(self.max_search_nodes, int)
            or isinstance(self.max_search_nodes, bool)
            or self.max_candidates_per_function < 1
            or self.max_search_nodes < 1
        ):
            raise ValueError("Los límites de búsqueda deben ser positivos.")


DEFAULT_DIAGNOSTIC_POLICY = DiagnosticPolicy()


@dataclass(frozen=True)
class DiagnosticGap:
    function_number: int
    required: int
    selected: int
    eligible_candidates: int
    reason: str

    @property
    def missing(self) -> int:
        return self.required - self.selected


@dataclass(frozen=True)
class DiagnosticResult:
    policy_version: str
    selection: tuple[DiagnosticCandidate, ...]
    gaps: tuple[DiagnosticGap, ...]
    functions: tuple[int, ...] = OPEC_FUNCTIONS
    search_exhausted: bool = False

    @property
    def complete(self) -> bool:
        return not self.gaps and not self.search_exhausted

    @property
    def diagnostic_valid(self) -> bool:
        """Only complete nine-function coverage is a diagnostic."""

        return self.complete

    @property
    def selected_by_function(self) -> dict[int, tuple[DiagnosticCandidate, ...]]:
        return {
            number: tuple(
                item for item in self.selection if item.function_number == number
            )
            for number in self.functions
        }


def _clean_identifier(value: object) -> str:
    return str(value or "").strip()


def _is_eligible(candidate: DiagnosticCandidate, policy: DiagnosticPolicy) -> bool:
    return (
        bool(_clean_identifier(candidate.question_id))
        and bool(_clean_identifier(candidate.case_id))
        and bool(_clean_identifier(candidate.revision_id))
        and candidate.function_number in OPEC_FUNCTIONS
        and (candidate.trusted or not policy.require_trusted)
        and str(candidate.bank_partition).strip().lower()
        in policy.allowed_partitions
        and str(candidate.question_type).strip().upper() == "SITUATIONAL"
        and str(candidate.track).strip().upper() == "FUNCIONAL"
    )


def _candidate_key(
    candidate: DiagnosticCandidate,
    partition_rank: dict[str, int],
) -> tuple:
    return (
        partition_rank[str(candidate.bank_partition).strip().lower()],
        _clean_identifier(candidate.question_id),
        _clean_identifier(candidate.case_id),
        _clean_identifier(candidate.revision_id),
    )


def _eligible_buckets(
    candidates: Iterable[DiagnosticCandidate],
    policy: DiagnosticPolicy,
    *,
    excluded_question_ids: frozenset[str],
    excluded_case_ids: frozenset[str],
    excluded_revision_ids: frozenset[str],
) -> dict[int, tuple[DiagnosticCandidate, ...]]:
    partition_rank = {
        partition: index for index, partition in enumerate(policy.partition_preference)
    }
    buckets: dict[int, dict[str, DiagnosticCandidate]] = {
        number: {} for number in OPEC_FUNCTIONS
    }
    for candidate in candidates:
        if not isinstance(candidate, DiagnosticCandidate) or not _is_eligible(
            candidate, policy
        ):
            continue
        question_id = _clean_identifier(candidate.question_id)
        case_id = _clean_identifier(candidate.case_id)
        revision_id = _clean_identifier(candidate.revision_id)
        if (
            question_id in excluded_question_ids
            or case_id in excluded_case_ids
            or revision_id in excluded_revision_ids
        ):
            continue
        normalized = DiagnosticCandidate(
            question_id=question_id,
            case_id=case_id,
            function_number=int(candidate.function_number),
            revision_id=revision_id,
            trusted=bool(candidate.trusted),
            bank_partition=str(candidate.bank_partition).strip().lower(),
            question_type="SITUATIONAL",
            track="FUNCIONAL",
        )
        previous = buckets[normalized.function_number].get(question_id)
        if previous is None or _candidate_key(normalized, partition_rank) < _candidate_key(
            previous, partition_rank
        ):
            buckets[normalized.function_number][question_id] = normalized

    return {
        number: tuple(
            sorted(
                values.values(),
                key=lambda item: _candidate_key(item, partition_rank),
            )[: policy.max_candidates_per_function]
        )
        for number, values in buckets.items()
    }


def select_diagnostic(
    candidates: Iterable[DiagnosticCandidate],
    policy: DiagnosticPolicy = DEFAULT_DIAGNOSTIC_POLICY,
    *,
    excluded_question_ids: Iterable[str] = (),
    excluded_case_ids: Iterable[str] = (),
    excluded_revision_ids: Iterable[str] = (),
) -> DiagnosticResult:
    """Select balanced items deterministically, or expose coverage gaps."""

    buckets = _eligible_buckets(
        candidates,
        policy,
        excluded_question_ids=frozenset(map(_clean_identifier, excluded_question_ids)),
        excluded_case_ids=frozenset(map(_clean_identifier, excluded_case_ids)),
        excluded_revision_ids=frozenset(map(_clean_identifier, excluded_revision_ids)),
    )
    slots = [
        function_number
        for function_number in OPEC_FUNCTIONS
        for _ in range(policy.items_per_function)
    ]
    # Most-constrained-first makes conflicts over case/revision IDs tractable.
    slots.sort(key=lambda number: (len(buckets[number]), number))

    best: tuple[DiagnosticCandidate, ...] = ()
    best_signature: Optional[tuple] = None
    node_count = 0
    search_exhausted = False

    def selection_signature(items: tuple[DiagnosticCandidate, ...]) -> tuple:
        return tuple(
            (item.function_number, item.question_id)
            for item in sorted(items, key=lambda value: (value.function_number, value.question_id))
        )

    def search(
        slot_index: int,
        chosen: tuple[DiagnosticCandidate, ...],
        used_questions: frozenset[str],
        used_cases: frozenset[str],
        used_revisions: frozenset[str],
        counts: tuple[int, ...],
    ) -> bool:
        nonlocal best, best_signature, node_count, search_exhausted
        node_count += 1
        if node_count > policy.max_search_nodes:
            search_exhausted = True
            return False

        signature = selection_signature(chosen)
        if len(chosen) > len(best) or (
            len(chosen) == len(best)
            and (best_signature is None or signature < best_signature)
        ):
            best = chosen
            best_signature = signature

        if slot_index == len(slots):
            return len(chosen) == len(slots)
        if len(chosen) + (len(slots) - slot_index) < len(best):
            return False

        function_number = slots[slot_index]
        function_index = function_number - 1
        if counts[function_index] >= policy.items_per_function:
            return search(
                slot_index + 1,
                chosen,
                used_questions,
                used_cases,
                used_revisions,
                counts,
            )

        for candidate in buckets[function_number]:
            case_id = _clean_identifier(candidate.case_id)
            revision_id = _clean_identifier(candidate.revision_id)
            if (
                candidate.question_id in used_questions
                or case_id in used_cases
                or revision_id in used_revisions
            ):
                continue
            next_counts = list(counts)
            next_counts[function_index] += 1
            if search(
                slot_index + 1,
                chosen + (candidate,),
                used_questions | {candidate.question_id},
                used_cases | {case_id},
                used_revisions | {revision_id},
                tuple(next_counts),
            ):
                return True
            if search_exhausted:
                return False

        # Skipping produces the best honest partial set when full coverage is
        # impossible. It never changes ``diagnostic_valid`` to true.
        return search(
            slot_index + 1,
            chosen,
            used_questions,
            used_cases,
            used_revisions,
            counts,
        )

    search(
        0,
        (),
        frozenset(),
        frozenset(),
        frozenset(),
        (0,) * len(OPEC_FUNCTIONS),
    )
    selection = tuple(
        sorted(best, key=lambda item: (item.function_number, item.question_id))
    )
    selected_counts = {
        number: sum(item.function_number == number for item in selection)
        for number in OPEC_FUNCTIONS
    }
    gaps = tuple(
        DiagnosticGap(
            function_number=number,
            required=policy.items_per_function,
            selected=selected_counts[number],
            eligible_candidates=len(buckets[number]),
            reason=(
                "sin candidatos elegibles"
                if not buckets[number]
                else "colisión de caso/revisión o cobertura insuficiente"
            ),
        )
        for number in OPEC_FUNCTIONS
        if selected_counts[number] < policy.items_per_function
    )
    return DiagnosticResult(
        policy_version=policy.version,
        selection=selection,
        gaps=gaps,
        search_exhausted=search_exhausted,
    )
