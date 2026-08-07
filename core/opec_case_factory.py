"""Reliable source-grounded fallback cases for OPEC onboarding."""


ADRES_SCENARIOS = (
    ("Gobierno de requisitos de una plataforma misional", "Un área solicita añadir funciones críticas cuando el desarrollo ya está avanzado; no hay priorización, línea base ni análisis del impacto en plazo, costo y seguridad.", "formalizar la necesidad, analizar impacto y someter el cambio al gobierno definido", "línea base, matriz de trazabilidad, análisis de impacto y decisión del control de cambios", "ampliar silenciosamente el alcance y aceptar entregas que no respondan a necesidades verificadas", "Gestión de requisitos", 10),
    ("Evaluación de seguridad de un servicio", "Una prueba revela una vulnerabilidad alta antes de liberar un servicio que procesa información sensible. El proveedor propone salir a producción y corregir después.", "detener la liberación, valorar el riesgo, exigir corrección y repetir las pruebas antes de autorizar", "informe de hallazgos, plan de tratamiento, resultados de la nueva prueba y aceptación del riesgo residual", "exponer información, afectar el servicio y aceptar un riesgo sin autoridad ni evidencia", "Seguridad y privacidad", 9),
    ("Control de cambios en producción", "Un incidente requiere modificar un componente compartido. El cambio no tiene pruebas de regresión, ventana aprobada ni procedimiento de reversión.", "tramitar un cambio de emergencia con evaluación, pruebas mínimas, responsables, ventana y reversión", "registro del cambio, evaluación técnica, resultados de pruebas, aprobaciones y evidencia posterior", "resolver un síntoma y provocar una interrupción mayor sin posibilidad de recuperación", "Gestión de cambios", 8),
    ("Interoperabilidad con entidades del sector", "Se intercambiarán datos con varias entidades mediante formatos distintos y credenciales compartidas. No están definidos propósito, datos mínimos ni responsabilidades.", "acordar el caso de uso, modelo de información, estándares, seguridad, responsabilidades y pruebas de interoperabilidad", "acuerdo de intercambio, catálogo de datos, especificación de interfaz, controles y resultados de pruebas", "generar inconsistencias, accesos indebidos y dependencias difíciles de auditar", "Interoperabilidad", 6),
    ("Administración de bases de datos", "Una base de datos misional presenta degradación y el equipo propone cambiar índices directamente en producción sin respaldo validado ni medición de línea base.", "diagnosticar con métricas, probar el ajuste en ambiente controlado, validar respaldo y programar el cambio", "línea base, plan de pruebas, respaldo restaurable, aprobación del cambio y comparación de resultados", "perder datos o empeorar el rendimiento sin poder identificar ni revertir la causa", "Bases de datos", 11),
    ("Arquitectura de una modernización", "Se quiere reemplazar una aplicación heredada que mantiene integraciones no documentadas. El proveedor recomienda un corte total en la primera entrega.", "caracterizar dependencias y datos, definir arquitectura de transición, migración verificable y retiro gradual", "catálogo de integraciones, arquitectura actual y objetivo, brechas, pruebas, conciliación y reversión", "interrumpir servicios o perder información al descubrir dependencias después del corte", "Arquitectura de software y TI", 12),
    ("Adopción responsable de inteligencia artificial", "Un piloto de analítica promete priorizar casos, pero usa datos sin evaluación de calidad y el modelo no permite explicar sus resultados.", "definir el caso de uso, validar datos, riesgos, explicabilidad, supervisión humana y criterios de éxito", "ficha del caso, evaluación de datos y riesgos, métricas, pruebas de sesgo y protocolo de supervisión", "automatizar decisiones opacas o discriminatorias y escalar resultados no confiables", "Tecnologías emergentes", 5),
    ("Estructuración de una adquisición tecnológica", "El estudio previo reproduce las especificaciones de un único fabricante y no relaciona la solución con capacidades, demanda ni costos de ciclo de vida.", "reformular la necesidad en términos funcionales, analizar alternativas, interoperabilidad, seguridad y costo total", "estudio del sector, análisis de alternativas, requisitos verificables, riesgos y estimación del ciclo de vida", "restringir injustificadamente la competencia y adquirir una solución costosa o dependiente", "Contratación de tecnología", 13),
    ("Supervisión de un contrato de servicios TI", "El proveedor reporta cumplimiento, pero los incidentes aumentan y las métricas entregadas excluyen periodos de indisponibilidad. Se acerca un pago importante.", "contrastar el informe con evidencia operativa, documentar incumplimientos y aplicar el procedimiento contractual", "mediciones independientes, tickets, actas, cálculo de niveles de servicio y requerimientos al contratista", "autorizar pagos sin soporte y debilitar la capacidad de exigir niveles de servicio", "Supervisión contractual", 14),
    ("Gestión del conocimiento y activos TI", "Al finalizar un contrato, repositorios, configuraciones y documentación están en cuentas del proveedor y el equipo interno no puede desplegar la solución.", "exigir transferencia controlada, inventario, versionamiento, accesos institucionales y prueba de despliegue", "repositorios institucionales, inventario, versiones, manuales, acta de transferencia y despliegue reproducible", "perder control del activo, continuidad y capacidad de mantener o auditar el servicio", "Gestión de activos y conocimiento", 7),
)


def build_fallback_opec_case(opec, case_number: int) -> dict:
    functions = list(getattr(opec, "functions", None) or [])
    scenario = ADRES_SCENARIOS[(case_number - 1) % len(ADRES_SCENARIOS)]
    title, situation, best_action, evidence, risk, competency, function_index = scenario
    function = functions[function_index] if len(functions) > function_index else getattr(opec, "purpose", "")
    text = (
        f"La Dirección de Gestión de Tecnologías de Información y Comunicaciones de ADRES asigna a "
        f"{getattr(opec, 'job_title', 'el profesional')} la siguiente situación: {situation} "
        f"El análisis debe considerar esta función de la OPEC 252097: {function}"
    )
    questions = [
        {
            "stem": "¿Cuál es la actuación inicial más adecuada frente a la solicitud?",
            "options": {"A": "Aceptar la alternativa más rápida y completar los controles al cierre.", "B": best_action.capitalize() + ".", "C": "Trasladar toda la decisión al proveedor sin establecer criterios institucionales."},
            "correct_key": "B",
            "rationale": "La función exige gestionar la necesidad con método, controles y alineación; la urgencia no elimina el análisis previo.",
            "track": "FUNCIONAL",
            "micro_competencia": competency,
            "macro_dominio": "Gestión institucional",
        },
        {
            "stem": "¿Qué evidencia permite controlar mejor la decisión adoptada?",
            "options": {"A": "Una comunicación informal sin responsables ni fecha.", "B": "La presentación comercial del proveedor como única fuente.", "C": evidence.capitalize() + "."},
            "correct_key": "C",
            "rationale": "La trazabilidad requiere evidencia verificable desde la definición hasta la aceptación y el seguimiento.",
            "track": "FUNCIONAL",
            "micro_competencia": competency,
            "macro_dominio": "Gestión institucional",
        },
        {
            "stem": "¿Cuál es el principal riesgo de atender la solicitud sin los controles indicados?",
            "options": {"A": risk.capitalize() + ".", "B": "Generar evidencia suficiente para sustentar la decisión.", "C": "Aumentar la participación de los responsables institucionales."},
            "correct_key": "A",
            "rationale": "Omitir diagnóstico, control y trazabilidad expone a la entidad a fallas técnicas, operativas y de cumplimiento.",
            "track": "FUNCIONAL",
            "micro_competencia": competency,
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
