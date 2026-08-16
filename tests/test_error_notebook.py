from datetime import datetime, timedelta

from core.error_notebook import (
    ERROR_CATEGORIES,
    TransferEvidence,
    build_error_guidance,
    evaluate_error_resolution,
    normalize_error_category,
)


OPENED = datetime(2026, 8, 10, 9, 0)


def _event(question_id, days, *, correct=True, novel=True, question_type="SITUATIONAL"):
    return TransferEvidence(
        question_id=question_id,
        revision_id=f"rev-{question_id}",
        correct=correct,
        occurred_at=OPENED + timedelta(days=days),
        is_novel=novel,
        question_type=question_type,
    )


def test_all_requested_error_categories_are_available():
    assert len(ERROR_CATEGORIES) == 10
    assert normalize_error_category("confusion_conceptual") == "concept_confusion"
    assert normalize_error_category("unknown") == "norm_unknown"


def test_guidance_works_without_ai_provider():
    guidance = build_error_guidance(
        category="missed_exception",
        user_reasoning="Apliqué la regla general.",
        rationale="Primero se verifica la excepción legal.",
        source_reference="Ley X, artículo 4",
    )
    assert guidance.category_label == "No identificar una excepción"
    assert "excepción" in guidance.why_it_failed
    assert guidance.source_to_review == "Ley X, artículo 4"
    assert guidance.user_reasoning == "Apliqué la regla general."


def test_same_or_immediate_question_never_closes_an_error():
    result = evaluate_error_resolution(
        original_question_id="q0",
        opened_at=OPENED,
        evidence=[_event("q0", 4), _event("q1", 1), _event("q1", 4, novel=False)],
    )
    assert result.overcome is False
    assert result.qualifying_transfer_count == 0


def test_two_distinct_delayed_transfer_questions_close_the_error():
    result = evaluate_error_resolution(
        original_question_id="q0",
        opened_at=OPENED,
        evidence=[_event("q1", 3), _event("q2", 5)],
    )
    assert result.overcome is True
    assert result.qualifying_transfer_count == 2


def test_likert_and_duplicate_revision_do_not_count_as_transfer():
    duplicate = _event("q1", 4)
    result = evaluate_error_resolution(
        original_question_id="q0",
        opened_at=OPENED,
        evidence=[
            duplicate,
            duplicate,
            _event("likert", 5, question_type="LIKERT"),
            _event("q2", 5, correct=False),
        ],
    )
    assert result.overcome is False
    assert result.qualifying_transfer_count == 1
