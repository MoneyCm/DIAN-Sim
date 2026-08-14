from types import SimpleNamespace

import pytest

from core.question_review import (
    QUALITY_ALL, QUALITY_PENDING, QUALITY_REINFORCEMENTS, QUALITY_VERIFIED,
    approve_candidate, candidate_validation_error, is_reinforcement_candidate,
    has_ai_audit, is_pending_review_candidate, matches_quality_filter, record_ai_audit, reject_candidate,
    review_queue_summary,
)


def candidate(**overrides):
    values = {
        "is_verified": False,
        "quality_report": {"status": "PENDING_REVIEW", "review": "reinforcement_candidate"},
        "source_refs": "Estatuto Tributario, artículo 1",
        "stem": "Situación y pregunta",
        "options_json": {"A": "Uno", "B": "Dos", "C": "Tres"},
        "correct_key": "A",
        "rationale": "La norma respalda la opción A.",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_valid_candidate_can_be_approved_for_active_practice():
    question = candidate()
    assert is_reinforcement_candidate(question)
    assert candidate_validation_error(question) is None
    approve_candidate(question, "admin")
    assert question.is_verified is True
    assert question.quality_report["review"] == "human_source_grounded"
    assert question.quality_report["origin"] == "reinforcement_candidate"


@pytest.mark.parametrize("field,value", [
    ("source_refs", ""),
    ("rationale", ""),
    ("options_json", {"A": "Uno", "B": "Dos", "C": "Tres", "D": "Cuatro"}),
    ("correct_key", "D"),
])
def test_incomplete_candidate_cannot_be_approved(field, value):
    question = candidate(**{field: value})
    assert candidate_validation_error(question)
    with pytest.raises(ValueError):
        approve_candidate(question, "admin")


def test_progressive_opec_question_can_be_individually_approved():
    question = candidate(
        quality_report={"origin": "progressive_opec_local", "guide_status": "pending"}
    )

    assert is_pending_review_candidate(question)
    assert candidate_validation_error(question) is None
    approve_candidate(question, "reviewer")

    assert question.is_verified is True
    assert question.quality_report["status"] == "APPROVED"
    assert question.quality_report["review"] == "human_source_grounded"
    assert question.quality_report["origin"] == "progressive_opec_local"
    assert question.quality_report["reviewed_by"] == "reviewer"
    assert question.quality_report["reviewed_at"]


def test_review_queue_counts_explicit_and_legacy_source_candidates():
    pending = candidate(
        quality_report={"origin": "progressive_opec_local", "guide_status": "pending"}
    )
    approved = candidate(
        is_verified=True,
        quality_report={"origin": "progressive_opec_local", "status": "APPROVED"},
    )
    rejected = candidate(
        quality_report={"origin": "progressive_opec_local", "status": "REJECTED"}
    )
    legacy = candidate(quality_report=None)

    summary = review_queue_summary([pending, approved, rejected, legacy])

    assert summary["total"] == 4
    assert summary["pending"] == 2
    assert summary["approved"] == 1
    assert summary["rejected"] == 1
    assert summary["next_question"] is pending


def test_review_queue_includes_legacy_unverified_question_with_source():
    legacy_candidate = candidate(quality_report=None)

    summary = review_queue_summary([legacy_candidate])

    assert summary["total"] == 1
    assert summary["pending"] == 1
    assert summary["next_question"] is legacy_candidate


def test_rejected_candidate_stays_out_of_active_study():
    question = candidate()
    reject_candidate(question, "admin", "Fuente insuficiente")
    assert question.is_verified is False
    assert question.quality_report["status"] == "REJECTED"
    assert question.quality_report["rejection_reason"] == "Fuente insuficiente"


def test_ai_audit_never_verifies_or_loses_candidate_state():
    question = candidate()
    assert not has_ai_audit(question)
    record_ai_audit(question, {"status": "APPROVED", "score": 10})
    assert question.is_verified is False
    assert is_reinforcement_candidate(question)
    assert has_ai_audit(question)
    assert question.quality_report["ai_audit"]["score"] == 10


def test_ai_audit_preserves_progressive_opec_queue_membership():
    question = candidate(
        quality_report={"origin": "progressive_opec_local", "guide_status": "pending"}
    )

    record_ai_audit(question, {"status": "IMPROVABLE", "score": 6})

    assert question.is_verified is False
    assert question.quality_report["origin"] == "progressive_opec_local"
    assert question.quality_report["ai_audit"]["status"] == "IMPROVABLE"


def test_quality_filters_separate_reinforcements_from_other_pending_items():
    reinforcement = candidate()
    legacy_pending = candidate(quality_report=None)
    verified = candidate(is_verified=True, quality_report={"status": "APPROVED"})
    assert matches_quality_filter(reinforcement, QUALITY_REINFORCEMENTS)
    assert not matches_quality_filter(legacy_pending, QUALITY_REINFORCEMENTS)
    assert matches_quality_filter(reinforcement, QUALITY_PENDING)
    assert matches_quality_filter(legacy_pending, QUALITY_PENDING)
    assert matches_quality_filter(verified, QUALITY_VERIFIED)
    assert all(matches_quality_filter(q, QUALITY_ALL) for q in (reinforcement, legacy_pending, verified))
