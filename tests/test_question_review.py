from types import SimpleNamespace

import pytest

from core.question_review import (
    QUALITY_ALL, QUALITY_PENDING, QUALITY_REINFORCEMENTS, QUALITY_VERIFIED,
    approve_candidate, automatic_rejection_reason, candidate_validation_error, is_reinforcement_candidate,
    has_ai_audit, is_pending_review_candidate, matches_quality_filter, record_ai_audit, reject_candidate,
    record_editorial_verification, review_queue_summary,
)


def candidate(**overrides):
    values = {
        "is_verified": False,
        "quality_report": {
            "status": "PENDING_REVIEW",
            "review": "reinforcement_candidate",
            "source_verification": {
                "status": "official_current",
                "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
                "locator": "Artículo 1",
                "supporting_excerpt": "Fragmento contrastado que sustenta de manera directa la respuesta A.",
                "verified_on": "2026-08-15",
                "verified_by": "editorial-test",
            },
            "editorial_difficulty_1_10": 5,
            "editorial_metadata": {
                "contract_version": "pjs-editorial-v2",
                "subtopic": "Facultades de fiscalización",
                "cognitive_level": "application",
                "function_number": 1,
                "distractor_explanations": {
                    "B": "Omite el procedimiento exigible para la actuación.",
                    "C": "Traslada indebidamente una competencia que debe conservarse.",
                },
            },
        },
        "source_refs": "Estatuto Tributario, artículo 1",
        "stem": (
            "En una actuación de fiscalización aparecen datos contradictorios. "
            "¿Cuál es la decisión inicial jurídicamente sustentada?"
        ),
        "options_json": {"A": "Uno", "B": "Dos", "C": "Tres"},
        "correct_key": "A",
        "rationale": "La norma respalda la opción A.",
        "track": "FUNCIONAL",
        "question_type": "SITUATIONAL",
        "competency": "Fiscalización",
        "topic": "Función 1",
        "difficulty": 2,
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
    base_report = candidate().quality_report
    question = candidate(
        quality_report={
            "origin": "progressive_opec_local",
            "guide_status": "pending",
            "source_verification": base_report["source_verification"],
            "editorial_difficulty_1_10": base_report["editorial_difficulty_1_10"],
            "editorial_metadata": base_report["editorial_metadata"],
        }
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
    verification = candidate().quality_report["source_verification"]
    pending = candidate(
        quality_report={
            "origin": "progressive_opec_local",
            "guide_status": "pending",
            "source_verification": verification,
        }
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
    base_report = candidate().quality_report
    question = candidate(
        quality_report={
            "origin": "progressive_opec_local",
            "guide_status": "pending",
            "source_verification": base_report["source_verification"],
            "editorial_difficulty_1_10": base_report["editorial_difficulty_1_10"],
            "editorial_metadata": base_report["editorial_metadata"],
        }
    )

    record_ai_audit(question, {"status": "IMPROVABLE", "score": 6})

    assert question.is_verified is False
    assert question.quality_report["origin"] == "progressive_opec_local"
    assert question.quality_report["ai_audit"]["status"] == "IMPROVABLE"


def test_invented_or_unverified_source_can_never_be_approved():
    invented = candidate(
        source_refs="Fuente inventada por proveedor",
        quality_report={"status": "PENDING_REVIEW", "review": "reinforcement_candidate"},
    )
    official_link_without_editorial_proof = candidate(
        source_refs="https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm, artículo 1",
        quality_report={"status": "PENDING_REVIEW", "review": "reinforcement_candidate"},
    )

    assert candidate_validation_error(invented)
    assert candidate_validation_error(official_link_without_editorial_proof)
    with pytest.raises(ValueError):
        approve_candidate(invented, "admin")
    with pytest.raises(ValueError):
        approve_candidate(official_link_without_editorial_proof, "admin")


def test_editorial_verification_records_source_difficulty_and_distractors():
    question = candidate(quality_report={"status": "PENDING_REVIEW"})

    record_editorial_verification(
        question,
        source_status="official_current",
        source_url="https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
        source_locator="Artículo 684",
        supporting_excerpt="La administración dispone de facultades de fiscalización para verificar obligaciones.",
        verified_on="2026-08-15",
        verified_by="admin",
        subtopic="Facultades de fiscalización",
        cognitive_level="application",
        function_number=1,
        editorial_difficulty=6,
        distractor_explanations={
            "B": "Omite la actuación procedente y la trazabilidad requerida.",
            "C": "Delega una competencia que corresponde a la dependencia responsable.",
        },
    )

    assert candidate_validation_error(question) is None
    assert question.quality_report["editorial_difficulty_1_10"] == 6
    assert question.quality_report["editorial_metadata"]["function_number"] == 1


def test_approval_blocks_missing_distractor_explanation():
    question = candidate()
    question.quality_report["editorial_metadata"]["distractor_explanations"].pop("C")

    assert candidate_validation_error(question) == "Falta explicar el distractor C."
    with pytest.raises(ValueError, match="distractor C"):
        approve_candidate(question, "admin")


def test_likert_candidate_uses_four_options_and_has_no_correct_key():
    question = candidate(
        track="COMPORTAMENTAL",
        question_type="LIKERT",
        options_json={
            "A": "Totalmente en desacuerdo",
            "B": "En desacuerdo",
            "C": "De acuerdo",
            "D": "Totalmente de acuerdo",
        },
        correct_key=None,
        rationale="Afirmación asociada a la competencia comportamental indicada.",
    )

    assert candidate_validation_error(question) is None
    approve_candidate(question, "admin")
    assert question.is_verified is True
    assert question.correct_key is None


def test_likert_candidate_rejects_key_or_three_option_scale():
    with_key = candidate(
        track="INTEGRIDAD",
        question_type="LIKERT",
        options_json={"A": "1", "B": "2", "C": "3", "D": "4"},
        correct_key="A",
    )
    three_options = candidate(
        track="COMPORTAMENTAL",
        question_type="LIKERT",
        correct_key=None,
    )

    assert candidate_validation_error(with_key)
    assert candidate_validation_error(three_options)


def test_automatic_rejection_only_retires_untraceable_or_explicitly_rejected_content():
    generated = candidate(source_refs="Mistral - Batch Gen v20")
    injected = candidate(source_refs="Inyección Especial Antigravity - OPEC 236769")
    audit_error_with_official_source = candidate(
        source_refs="Decreto 1165 de 2019, artículo 172",
    )
    record_ai_audit(audit_error_with_official_source, {"status": "ERROR", "score": 0})
    explicitly_rejected = candidate(source_refs="Fuente oficial")
    record_ai_audit(explicitly_rejected, {"status": "REJECTED", "score": 3})

    assert automatic_rejection_reason(generated)
    assert automatic_rejection_reason(injected)
    assert automatic_rejection_reason(audit_error_with_official_source) is None
    assert automatic_rejection_reason(explicitly_rejected)


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
