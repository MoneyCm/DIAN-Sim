from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

import pytest

from core.readiness_gate import (
    BankEvidence,
    ItemResult,
    MeasurementSessionResult,
    ReadinessPolicy,
    RetentionEvidence,
    evaluate_readiness,
)


NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
POLICY = ReadinessPolicy(
    version="phase2-test-v1",
    target_score=85.0,
    required_sessions=3,
    minimum_functional_items_per_session=20,
    max_session_age_days=30,
    minimum_retention_delay_days=7,
    minimum_retention_functional_items=9,
)


def _items(prefix: str, *, total: int = 20, correct: int = 17):
    return tuple(
        ItemResult(
            revision_id=f"{prefix}-revision-{index}",
            case_id=f"{prefix}-case-{index}",
            function_number=(index % 9) + 1,
            is_correct=index < correct,
        )
        for index in range(total)
    )


def _session(index: int) -> MeasurementSessionResult:
    prefix = f"s{index}"
    return MeasurementSessionResult(
        session_id=prefix,
        user_id=7,
        competition_id=2676,
        opec_number="236769",
        policy_version=POLICY.version,
        blueprint_version="blueprint-236769-v1",
        started_at=NOW - timedelta(days=index + 1, minutes=40),
        completed_at=NOW - timedelta(days=index + 1),
        items=_items(prefix),
    )


def _bank(sessions, retention=None, **overrides) -> BankEvidence:
    trusted_ids = {
        item.revision_id
        for session in sessions
        for item in session.items
        if item.track == "FUNCIONAL" and item.question_type != "LIKERT"
    }
    if retention is not None:
        trusted_ids.update(
            item.revision_id
            for item in retention.items
            if item.track == "FUNCIONAL" and item.question_type != "LIKERT"
        )
    values = {
        "sources_verified": True,
        "measurement_bank_trusted": True,
        "trusted_revision_ids": frozenset(trusted_ids),
        "note": "Citas y revisiones verificadas",
    }
    values.update(overrides)
    return BankEvidence(**values)


def _base_sessions():
    return [_session(0), _session(1), _session(2)]


def test_exactly_85_meets_only_the_safe_internal_goal_and_accepts_dicts():
    sessions = _base_sessions()
    assessment = evaluate_readiness(
        [asdict(session) for session in sessions],
        bank_evidence=asdict(_bank(sessions)),
        policy=POLICY,
        as_of=NOW,
    )

    assert assessment.internal_precision_goal_met is True
    assert assessment.session_scores == (85.0, 85.0, 85.0)
    assert assessment.precision_target_label == "objetivo interno de precisión"
    assert assessment.repeated_target_label == "meta interna repetida 3/3"
    assert assessment.claim_status == "internal_diagnostic_not_official_result"
    assert assessment.official_functional_minimum_label == "mínimo oficial funcional"
    assert assessment.official_functional_minimum_score == 70.0
    assert assessment.official_result is None
    assert assessment.internal_retention_goal_met is None
    assert assessment.retention_gate.status == "pending"


def test_84_99_does_not_meet_the_85_internal_target():
    sessions = _base_sessions()
    historical_items = tuple(
        replace(item, is_correct=None) for item in sessions[0].items
    )
    sessions[0] = replace(
        sessions[0], items=historical_items, functional_score=84.99
    )

    assessment = evaluate_readiness(
        sessions,
        bank_evidence=_bank(sessions),
        policy=POLICY,
        as_of=NOW,
    )

    assert assessment.internal_precision_goal_met is False
    assert assessment.gate("functional_precision_target").met is False
    assert assessment.repeated_target_label == "meta interna repetida 2/3"
    assert 84.99 in assessment.session_scores


def test_fewer_than_three_sessions_fails_the_count_gate():
    sessions = _base_sessions()[:2]
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    assert assessment.gate("measurement_session_count").met is False
    assert assessment.internal_precision_goal_met is False


def test_an_incomplete_session_cannot_count_as_measurement_evidence():
    sessions = _base_sessions()
    sessions[0] = replace(sessions[0], completed=False)
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    assert assessment.gate("completed_sessions").met is False
    assert assessment.internal_precision_goal_met is False


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [("feedback_enabled", True), ("aids_used", True)],
)
def test_feedback_or_aids_invalidate_a_measurement_session(field_name, field_value):
    sessions = _base_sessions()
    sessions[0] = replace(sessions[0], **{field_name: field_value})
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    assert assessment.gate("no_feedback_or_aids").met is False


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("user_id", 99),
        ("competition_id", 9999),
        ("opec_number", "other-opec"),
        ("policy_version", "other-policy"),
        ("blueprint_version", "other-blueprint"),
    ],
)
def test_mixed_user_competition_opec_or_versions_fail_closed(field_name, field_value):
    sessions = _base_sessions()
    sessions[0] = replace(sessions[0], **{field_name: field_value})
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    assert assessment.gate("same_versioned_context").met is False
    assert assessment.internal_precision_goal_met is False


def test_only_measurement_partition_is_eligible():
    sessions = _base_sessions()
    sessions[0] = replace(sessions[0], bank_partition="training")
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    assert assessment.gate("measurement_partition").met is False


@pytest.mark.parametrize("repeated_field", ["revision_id", "case_id"])
def test_repeated_revision_or_case_between_sessions_fails(repeated_field):
    sessions = _base_sessions()
    replacement = {
        repeated_field: getattr(sessions[1].items[0], repeated_field)
    }
    changed_item = replace(sessions[0].items[0], **replacement)
    sessions[0] = replace(
        sessions[0], items=(changed_item,) + sessions[0].items[1:]
    )
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    uniqueness = assessment.gate("no_repeated_measurement_material")
    assert uniqueness.met is False
    assert uniqueness.evidence[
        "repeated_revision_ids" if repeated_field == "revision_id" else "repeated_case_ids"
    ]


def test_joint_coverage_requires_all_nine_functions():
    sessions = _base_sessions()
    sessions = [
        replace(
            session,
            items=tuple(
                replace(item, function_number=8)
                if item.function_number == 9
                else item
                for item in session.items
            ),
        )
        for session in sessions
    ]
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    coverage = assessment.gate("joint_function_coverage")
    assert coverage.met is False
    assert coverage.evidence["missing"] == (9,)


def test_sessions_outside_the_editable_recency_window_do_not_pass():
    sessions = _base_sessions()
    sessions[2] = replace(sessions[2], completed_at=NOW - timedelta(days=31))
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    assert assessment.gate("recent_sessions").met is False


def test_likert_items_are_excluded_from_score_total_coverage_and_repetition():
    sessions = _base_sessions()
    likert = tuple(
        ItemResult(
            revision_id=f"likert-{index}",
            case_id="shared-likert-case",
            function_number=None,
            is_correct=False,
            track="COMPORTAMENTAL",
            question_type="LIKERT",
        )
        for index in range(50)
    )
    sessions = [replace(session, items=session.items + likert) for session in sessions]
    assessment = evaluate_readiness(
        sessions, bank_evidence=_bank(sessions), policy=POLICY, as_of=NOW
    )

    assert assessment.internal_precision_goal_met is True
    assert assessment.session_scores == (85.0, 85.0, 85.0)
    assert assessment.gate("minimum_functional_total").evidence["totals"] == (
        20,
        20,
        20,
    )
    assert assessment.gate("no_repeated_measurement_material").met is True


def test_minimum_functional_total_is_editable_and_enforced_per_session():
    sessions = _base_sessions()
    stricter_policy = replace(POLICY, minimum_functional_items_per_session=21)
    assessment = evaluate_readiness(
        sessions,
        bank_evidence=_bank(sessions),
        policy=stricter_policy,
        as_of=NOW,
    )

    assert assessment.gate("minimum_functional_total").met is False


def test_untrusted_sources_or_bank_fail_the_quality_gate():
    sessions = _base_sessions()
    evidence = _bank(sessions, sources_verified=False)
    assessment = evaluate_readiness(
        sessions, bank_evidence=evidence, policy=POLICY, as_of=NOW
    )

    assert assessment.gate("trusted_sources_and_bank").met is False


def _retention(*, days_after_anchor: int) -> RetentionEvidence:
    anchor = NOW - timedelta(days=10)
    return RetentionEvidence(
        retention_id="retention-1",
        user_id=7,
        competition_id=2676,
        opec_number="236769",
        policy_version=POLICY.version,
        blueprint_version="blueprint-236769-v1",
        anchor_at=anchor,
        measured_at=anchor + timedelta(days=days_after_anchor),
        items=_items("retention", total=9, correct=8),
    )


def test_delayed_retention_is_a_separate_internal_gate():
    sessions = _base_sessions()
    retention = _retention(days_after_anchor=8)
    assessment = evaluate_readiness(
        sessions,
        bank_evidence=_bank(sessions, retention),
        policy=POLICY,
        retention=retention,
        as_of=NOW,
    )

    assert assessment.internal_precision_goal_met is True
    assert assessment.internal_retention_goal_met is True
    assert assessment.retention_gate.met is True
    assert assessment.status == "internal_precision_and_retention_evidence_met"
    assert assessment.official_result is None


def test_retention_before_the_editable_delay_stays_not_met_without_official_result():
    sessions = _base_sessions()
    retention = _retention(days_after_anchor=6)
    assessment = evaluate_readiness(
        sessions,
        bank_evidence=_bank(sessions, retention),
        policy=POLICY,
        retention=retention,
        as_of=NOW,
    )

    assert assessment.internal_precision_goal_met is True
    assert assessment.internal_retention_goal_met is False
    assert assessment.retention_gate.met is False
    assert assessment.status == "internal_precision_met_retention_not_met"
    assert assessment.official_result is None


def test_more_than_three_sessions_uses_the_newest_three():
    sessions = _base_sessions()
    older = replace(
        _session(9),
        session_id="older",
        completed_at=NOW - timedelta(days=20),
        items=_items("older", total=20, correct=0),
    )
    history = sessions + [older]
    assessment = evaluate_readiness(
        history, bank_evidence=_bank(history), policy=POLICY, as_of=NOW
    )

    assert assessment.selected_session_ids == ("s0", "s1", "s2")
    assert assessment.internal_precision_goal_met is True
