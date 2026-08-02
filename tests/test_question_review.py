from types import SimpleNamespace

import pytest

from core.question_review import (
    approve_candidate, candidate_validation_error, is_reinforcement_candidate,
    record_ai_audit, reject_candidate,
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


def test_rejected_candidate_stays_out_of_active_study():
    question = candidate()
    reject_candidate(question, "admin", "Fuente insuficiente")
    assert question.is_verified is False
    assert question.quality_report["status"] == "REJECTED"
    assert question.quality_report["rejection_reason"] == "Fuente insuficiente"


def test_ai_audit_never_verifies_or_loses_candidate_state():
    question = candidate()
    record_ai_audit(question, {"status": "APPROVED", "score": 10})
    assert question.is_verified is False
    assert is_reinforcement_candidate(question)
    assert question.quality_report["ai_audit"]["score"] == 10
