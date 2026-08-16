from types import SimpleNamespace

from core.question_opec_scope import (
    question_matches_opec,
    question_opec_number,
    stamp_question_opec,
)


def item(**overrides):
    values = {
        "question_id": "q-1",
        "case_id": None,
        "case_study": None,
        "topic": "Tema",
        "micro_competencia": "",
        "competency": "",
        "source_refs": "",
        "stem": "",
        "quality_report": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_scope_prefers_explicit_review_metadata():
    question = item(
        topic="OPEC 242699",
        quality_report={"scope": {"opec_number": "236769"}},
    )
    assert question_opec_number(question) == "236769"
    assert question_matches_opec(question, "236769")


def test_scope_detects_opec_in_topic_or_case_identifier():
    assert question_opec_number(item(topic="OPEC 252097 · Función 4")) == "252097"
    assert question_opec_number(item(case_id="goa-236769-tributario-01")) == "236769"


def test_ambiguous_or_unscoped_material_is_not_shared_between_opecs():
    assert question_opec_number(item(topic="OPEC 236769 y OPEC 242699")) is None
    assert not question_matches_opec(item(topic="Fiscalización general"), "236769")


def test_stamp_preserves_quality_report_and_records_scope():
    question = item(quality_report={"status": "APPROVED"})
    stamp_question_opec(question, "236769")
    assert question.quality_report == {
        "status": "APPROVED",
        "scope": {"opec_number": "236769"},
    }
