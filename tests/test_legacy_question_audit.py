from core.legacy_question_audit import KEEP_PRACTICE, RETIRE, REWRITE, legacy_audit_decision


def test_verified_legacy_families_get_conservative_decisions():
    assert legacy_audit_decision("OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Término de Firmeza de Declaración")[0] == KEEP_PRACTICE
    assert legacy_audit_decision("OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Notificación Electrónica de Actos")[0] == RETIRE
    assert legacy_audit_decision("OPEC 236769 - Recurso de Reconsideración Plazo")[0] == REWRITE
