from __future__ import annotations

import pytest

from core.diagnostic import (
    DiagnosticCandidate,
    DiagnosticPolicy,
    select_diagnostic,
)


def candidate(
    function_number: int,
    suffix: str = "1",
    *,
    case_id: str | None = None,
    revision_id: str | None = None,
    trusted: bool = True,
    bank_partition: str = "measurement",
    question_type: str = "SITUATIONAL",
    track: str = "FUNCIONAL",
) -> DiagnosticCandidate:
    return DiagnosticCandidate(
        question_id=f"q-f{function_number}-{suffix}",
        case_id=case_id if case_id is not None else f"case-f{function_number}-{suffix}",
        function_number=function_number,
        revision_id=(
            revision_id if revision_id is not None else f"rev-f{function_number}-{suffix}"
        ),
        trusted=trusted,
        bank_partition=bank_partition,
        question_type=question_type,
        track=track,
    )


def complete_candidates(*, partition: str = "measurement"):
    return [
        candidate(number, bank_partition=partition)
        for number in range(1, 10)
    ]


def test_complete_diagnostic_is_balanced_unique_and_order_stable():
    items = complete_candidates()

    first = select_diagnostic(items)
    reversed_input = select_diagnostic(reversed(items))

    assert first == reversed_input
    assert first.complete is True
    assert first.diagnostic_valid is True
    assert first.gaps == ()
    assert len(first.selection) == 9
    assert [item.function_number for item in first.selection] == list(range(1, 10))
    assert len({item.case_id for item in first.selection}) == 9
    assert len({item.revision_id for item in first.selection}) == 9


def test_measurement_is_preferred_but_training_can_fill_a_conflict():
    items = complete_candidates()
    items.extend(
        [
            candidate(
                1,
                "measurement-shared",
                case_id="case-needed-by-f2",
                bank_partition="measurement",
            ),
            candidate(
                1,
                "training-fallback",
                case_id="case-training-f1",
                bank_partition="training",
            ),
            candidate(
                2,
                "only-shared",
                case_id="case-needed-by-f2",
                bank_partition="measurement",
            ),
        ]
    )
    # Remove the original f1/f2 so the conflict is required rather than merely
    # another optional path.
    items = [item for item in items if not (item.function_number in {1, 2} and item.question_id in {"q-f1-1", "q-f2-1"})]

    result = select_diagnostic(items)

    assert result.complete is True
    selected = result.selected_by_function
    assert selected[1][0].bank_partition == "training"
    assert selected[2][0].case_id == "case-needed-by-f2"


@pytest.mark.parametrize(
    "allowed,expected",
    [
        (("measurement",), "measurement"),
        (("training",), "training"),
    ],
)
def test_policy_controls_training_and_measurement_partitions(allowed, expected):
    items = []
    for number in range(1, 10):
        items.extend(
            [
                candidate(number, "m", bank_partition="measurement"),
                candidate(number, "t", bank_partition="training"),
            ]
        )
    policy = DiagnosticPolicy(
        allowed_partitions=allowed,
        partition_preference=allowed,
    )

    result = select_diagnostic(items, policy)

    assert result.complete is True
    assert {item.bank_partition for item in result.selection} == {expected}


def test_filters_untrusted_nonfunctional_non_situational_and_incomplete_ids():
    items = complete_candidates()
    items = [item for item in items if item.function_number != 9]
    items.extend(
        [
            candidate(9, "untrusted", trusted=False),
            candidate(9, "behavioral", track="COMPORTAMENTAL"),
            candidate(9, "likert", question_type="LIKERT"),
            candidate(9, "reserved", bank_partition="reserved"),
            candidate(9, "missing-case", case_id=""),
            candidate(9, "missing-revision", revision_id=""),
        ]
    )

    result = select_diagnostic(items)

    assert result.complete is False
    assert result.diagnostic_valid is False
    assert len(result.selection) == 8
    assert [gap.function_number for gap in result.gaps] == [9]
    assert result.gaps[0].eligible_candidates == 0


def test_insufficient_function_coverage_returns_honest_partial_selection():
    result = select_diagnostic(complete_candidates()[:-1])

    assert result.complete is False
    assert result.diagnostic_valid is False
    assert len(result.selection) == 8
    assert result.gaps[0].function_number == 9
    assert result.gaps[0].missing == 1


def test_shared_case_and_revision_are_never_repeated():
    items = complete_candidates()
    items = [item for item in items if item.function_number not in {1, 2}]
    items.extend(
        [
            candidate(1, "preferred", case_id="shared-case"),
            candidate(1, "fallback", case_id="unique-f1"),
            candidate(2, "only", case_id="shared-case"),
            candidate(2, "revision-conflict", revision_id="shared-revision"),
            candidate(3, "extra", revision_id="shared-revision"),
        ]
    )

    result = select_diagnostic(items)

    assert result.complete is True
    assert len({item.case_id for item in result.selection}) == 9
    assert len({item.revision_id for item in result.selection}) == 9


def test_two_items_per_function_remain_balanced():
    items = [
        candidate(number, suffix)
        for number in range(1, 10)
        for suffix in ("a", "b")
    ]
    policy = DiagnosticPolicy(items_per_function=2)

    result = select_diagnostic(items, policy)

    assert result.complete is True
    assert len(result.selection) == 18
    assert {
        number: len(selected)
        for number, selected in result.selected_by_function.items()
    } == {number: 2 for number in range(1, 10)}


def test_prior_exposure_exclusions_create_visible_gap_instead_of_reuse():
    items = complete_candidates()
    first = items[0]

    result = select_diagnostic(
        items,
        excluded_question_ids=[first.question_id],
        excluded_case_ids=[first.case_id],
        excluded_revision_ids=[first.revision_id],
    )

    assert result.complete is False
    assert [gap.function_number for gap in result.gaps] == [1]
    assert all(item.function_number != 1 for item in result.selection)


def test_bounded_search_never_claims_completeness_when_exhausted():
    policy = DiagnosticPolicy(max_search_nodes=1)

    result = select_diagnostic(complete_candidates(), policy)

    assert result.search_exhausted is True
    assert result.complete is False
    assert result.diagnostic_valid is False
    assert result.gaps


@pytest.mark.parametrize(
    "kwargs",
    [
        {"items_per_function": 0},
        {"allowed_partitions": ("reserved",), "partition_preference": ("reserved",)},
        {"allowed_partitions": ("training",), "partition_preference": ("measurement",)},
        {"max_candidates_per_function": 0},
        {"max_search_nodes": 0},
    ],
)
def test_invalid_diagnostic_policy_is_rejected(kwargs):
    with pytest.raises(ValueError):
        DiagnosticPolicy(**kwargs)
