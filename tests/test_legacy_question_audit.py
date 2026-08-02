from types import SimpleNamespace

from core.legacy_question_audit import (
    KEEP_PRACTICE, RETIRE, REWRITE, is_safe_for_active_study, legacy_audit_decision,
)


def test_verified_legacy_families_get_conservative_decisions():
    assert legacy_audit_decision("OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Término de Firmeza de Declaración")[0] == KEEP_PRACTICE
    assert legacy_audit_decision("OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Notificación Electrónica de Actos")[0] == RETIRE
    assert legacy_audit_decision("OPEC 236769 - Recurso de Reconsideración Plazo")[0] == REWRITE


def test_active_study_excludes_rewrite_and_retire_questions():
    grounded = SimpleNamespace(is_verified=True, quality_report={"review": "human_source_grounded"})
    kept = SimpleNamespace(is_verified=True, quality_report={"legacy_audit": {"decision": KEEP_PRACTICE}})
    rewrite = SimpleNamespace(is_verified=True, quality_report={"legacy_audit": {"decision": REWRITE}})
    retired = SimpleNamespace(is_verified=True, quality_report={"legacy_audit": {"decision": RETIRE}})
    assert is_safe_for_active_study(grounded)
    assert is_safe_for_active_study(kept)
    assert not is_safe_for_active_study(rewrite)
    assert not is_safe_for_active_study(retired)
