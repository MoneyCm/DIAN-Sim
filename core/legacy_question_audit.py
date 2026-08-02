"""Conservative human audit decisions for the legacy OPEC 236769 bank."""

KEEP_PRACTICE = "KEEP_PRACTICE"
REWRITE = "REWRITE"
RETIRE = "RETIRE"

KEEP_TOPICS = {
    "OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Término de Firmeza de Declaración": "Regla general de tres años del artículo 714 verificada.",
    "OPEC 236769 - Precrítica y Clasificación de Insumos - Requerimiento Ordinario de Información": "Facultad general de fiscalización del artículo 684 verificada.",
    "OPEC 236769 - Práctica de Pruebas e Inspección Tributaria - Valor Probatorio de Libros": "Valor probatorio condicionado de la contabilidad, artículo 772, verificado.",
}

RETIRE_TOPICS = {
    "OPEC 236769 - Precrítica y Clasificación de Insumos - Clasificación de Insumos": "Usa la categoría no sustentada 'Inexactitud de Corrección Inmediata'.",
    "OPEC 236769 - Proferir Actos Administrativos de Trámite y Fondo - Notificación Electrónica de Actos": "Confunde fecha de notificación con inicio del término de respuesta del artículo 566-1.",
    "OPEC 236769 - Notificación Electrónica de Actos": "Confunde fecha de notificación con inicio del término de respuesta del artículo 566-1.",
    "OPEC 236769 - Análisis Preliminar de Denuncias - Pertinencia de Denuncia": "Propone actos alternativos sin fuente procedimental suficiente.",
    "OPEC 236769 - Análisis Preliminar de Denuncias - Reserva de Identidad del Denunciante": "Afirma reserva absoluta sin identificar una fuente legal específica.",
}


def legacy_audit_decision(topic: str) -> tuple[str, str]:
    if topic in KEEP_TOPICS:
        return KEEP_PRACTICE, KEEP_TOPICS[topic]
    if topic in RETIRE_TOPICS:
        return RETIRE, RETIRE_TOPICS[topic]
    return REWRITE, "No es segura para uso activo sin reescritura y verificación normativa específica."


def is_safe_for_active_study(question) -> bool:
    """Allow only grounded GOA questions or legacy items explicitly retained."""
    if not bool(getattr(question, "is_verified", False)):
        return False
    report = getattr(question, "quality_report", None)
    if not isinstance(report, dict):
        return False
    if report.get("review") in {"human_source_grounded", "source_grounded"}:
        return True
    return (report.get("legacy_audit") or {}).get("decision") == KEEP_PRACTICE
