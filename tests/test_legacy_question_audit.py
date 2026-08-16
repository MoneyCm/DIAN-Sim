from types import SimpleNamespace

from core.legacy_question_audit import (
    KEEP_PRACTICE, RETIRE, REWRITE, is_safe_for_active_study, legacy_audit_decision,
)


SOURCE_VERIFICATION = {
    "status": "official_current",
    "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
    "locator": "Artículo 684",
    "supporting_excerpt": "La Administración Tributaria tiene amplias facultades de fiscalización.",
    "verified_on": "2026-08-15",
    "verified_by": "prueba editorial",
}


def test_verified_legacy_families_get_conservative_decisions():
    assert legacy_audit_decision("OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Término de Firmeza de Declaración")[0] == KEEP_PRACTICE
    assert legacy_audit_decision("OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Notificación Electrónica de Actos")[0] == RETIRE
    assert legacy_audit_decision("OPEC 236769 - Recurso de Reconsideración Plazo")[0] == REWRITE


def test_active_study_excludes_rewrite_and_retire_questions():
    structural = {
        "stem": "Ante un hallazgo documentado, ¿cuál actuación protege el debido proceso?",
        "options_json": {"A": "Aplicar el procedimiento.", "B": "Omitirlo.", "C": "Delegarlo."},
        "correct_key": "A",
        "rationale": "La actuación debe conservar competencia, motivación y trazabilidad.",
        "source_refs": "Estatuto Tributario, artículo 684",
        "difficulty": 2,
        "competency": "Fiscalización",
        "topic": "Función 1",
        "track": "FUNCIONAL",
        "question_type": "SITUATIONAL",
    }
    grounded = SimpleNamespace(**structural, is_verified=True, quality_report={
        "review": "human_source_grounded",
        "source_verification": SOURCE_VERIFICATION,
    })
    kept = SimpleNamespace(**structural, is_verified=True, quality_report={
        "legacy_audit": {"decision": KEEP_PRACTICE},
        "source_verification": SOURCE_VERIFICATION,
    })
    rewrite = SimpleNamespace(is_verified=True, quality_report={"legacy_audit": {"decision": REWRITE}})
    retired = SimpleNamespace(is_verified=True, quality_report={"legacy_audit": {"decision": RETIRE}})
    assert is_safe_for_active_study(grounded)
    assert is_safe_for_active_study(kept)
    assert not is_safe_for_active_study(rewrite)
    assert not is_safe_for_active_study(retired)


def test_historical_review_label_without_precise_source_is_not_active():
    legacy = SimpleNamespace(
        is_verified=True,
        quality_report={"review": "human_source_grounded"},
    )
    assert not is_safe_for_active_study(legacy)
