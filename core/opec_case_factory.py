"""Reliable source-grounded fallback cases for OPEC onboarding."""


def build_fallback_opec_case(opec, case_number: int) -> dict:
    functions = list(getattr(opec, "functions", None) or [])
    function = functions[(case_number - 1) % len(functions)] if functions else getattr(opec, "purpose", "")
    title = f"Caso {case_number}: decisión técnica y control institucional"
    text = (
        f"En el cargo {getattr(opec, 'job_title', 'profesional')}, la dependencia recibe una solicitud "
        "urgente que debe ejecutarse sin diagnóstico, responsables definidos ni evidencia de cumplimiento. "
        f"La actuación se relaciona con esta función del empleo: {function}. "
        "El equipo debe responder manteniendo continuidad, seguridad, trazabilidad y alineación institucional."
    )
    questions = [
        {
            "stem": "¿Cuál es la actuación inicial más adecuada frente a la solicitud?",
            "options": {
                "A": "Ejecutarla inmediatamente y documentarla cuando termine.",
                "B": "Precisar necesidad, alcance, riesgos, responsables y criterios de aceptación antes de definir la ejecución.",
                "C": "Rechazarla porque toda solicitud urgente incumple la planeación institucional.",
            },
            "correct_key": "B",
            "rationale": "La función exige gestionar la necesidad con método, controles y alineación; la urgencia no elimina el análisis previo.",
            "track": "FUNCIONAL",
            "micro_competencia": "Gestión y planeación de TI",
            "macro_dominio": "Gestión institucional",
        },
        {
            "stem": "¿Qué evidencia permite controlar mejor la decisión adoptada?",
            "options": {
                "A": "Una conversación informal con el solicitante.",
                "B": "La factura del proveedor, aunque no describa alcance ni aceptación.",
                "C": "Un registro aprobado de requisitos, riesgos, responsables, controles, pruebas y criterios de aceptación.",
            },
            "correct_key": "C",
            "rationale": "La trazabilidad requiere evidencia verificable desde la definición hasta la aceptación y el seguimiento.",
            "track": "FUNCIONAL",
            "micro_competencia": "Trazabilidad y control",
            "macro_dominio": "Gestión institucional",
        },
        {
            "stem": "¿Cuál es el principal riesgo de atender la solicitud sin los controles indicados?",
            "options": {
                "A": "Afectar la continuidad, seguridad o calidad y no poder demostrar por qué se tomó la decisión.",
                "B": "Producir demasiada evidencia para una auditoría futura.",
                "C": "Impedir que el proveedor elija por sí solo la solución institucional.",
            },
            "correct_key": "A",
            "rationale": "Omitir diagnóstico, control y trazabilidad expone a la entidad a fallas técnicas, operativas y de cumplimiento.",
            "track": "FUNCIONAL",
            "micro_competencia": "Gestión de riesgos",
            "macro_dominio": "Gestión institucional",
        },
    ]
    return {"title": title, "text": text, "questions": questions}


def build_fallback_questions(opec, category: str, count: int, start_index: int = 0) -> list[dict]:
    """Build unique three-option practice questions without consuming an API quota."""
    functions = list(getattr(opec, "functions", None) or [])
    purpose = getattr(opec, "purpose", "") or "cumplir el propósito institucional"
    job_title = getattr(opec, "job_title", "el empleo")
    result = []
    for offset in range(count):
        number = start_index + offset + 1
        function = functions[(number - 1) % len(functions)] if functions else purpose
        if category == "FUNCIONAL":
            stem = (
                f"Situación {number}. En {job_title} se solicita actuar sobre esta función: {function} "
                "¿Cuál respuesta ofrece mayor control institucional?"
            )
            options = {
                "A": "Ejecutar la solicitud sin análisis para reducir el tiempo de respuesta.",
                "B": "Definir necesidad, alcance, riesgos, responsables, controles y evidencia de aceptación antes de ejecutar.",
                "C": "Delegar completamente la decisión al proveedor o al área solicitante.",
            }
            correct = "B"
            rationale = "La gestión profesional exige una decisión trazable, basada en riesgos y alineada con la función del empleo."
        elif category == "INTEGRIDAD":
            stem = (
                f"Dilema {number}. Durante una decisión relacionada con {function}, un interesado ofrece acelerar el trámite "
                "si se omiten controles. ¿Qué debe hacer el servidor público?"
            )
            options = {
                "A": "Aceptar si considera que el resultado beneficiará a la entidad.",
                "B": "Omitir el ofrecimiento y continuar sin dejar registro.",
                "C": "Rechazarlo, mantener los controles, documentar la situación y reportarla por el canal correspondiente.",
            }
            correct = "C"
            rationale = "Honestidad, transparencia y diligencia exigen rechazar ventajas, conservar controles y dejar trazabilidad."
        else:
            stem = (
                f"Escenario {number}. El equipo responsable de {function} presenta desacuerdos que amenazan el resultado. "
                "¿Cuál actuación demuestra mejor competencia comportamental?"
            )
            options = {
                "A": "Aclarar el objetivo, escuchar evidencia, acordar responsabilidades y hacer seguimiento a compromisos.",
                "B": "Imponer una solución sin escuchar al equipo para evitar más discusión.",
                "C": "Posponer indefinidamente la decisión hasta que todos coincidan espontáneamente.",
            }
            correct = "A"
            rationale = "El trabajo colaborativo orientado a resultados combina escucha, claridad, responsabilidad y seguimiento."
        result.append({
            "stem": stem,
            "options": options,
            "correct_key": correct,
            "rationale": rationale,
        })
    return result
