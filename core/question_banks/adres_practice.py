"""Diversified provisional practice bank for ADRES OPEC 252097."""

from dataclasses import dataclass


SOURCE_VERSION = "OPEC 252097 · banco base provisional opec-2026-08-v1 · guía oficial pendiente"


@dataclass(frozen=True)
class FunctionProfile:
    number: int
    competency: str
    topic: str
    action: str
    evidence: str
    risk: str


FUNCTION_PROFILES = (
    FunctionProfile(1, "Gobierno de proyectos TI", "Políticas y metodologías de proyectos TI", "definir gobierno, ciclo de vida, roles, controles y criterios de éxito", "metodología aprobada, matriz RACI, hitos y registro de decisiones", "ejecutar proyectos sin prioridades, responsables ni control comparable"),
    FunctionProfile(2, "Gobierno de seguridad", "Políticas de seguridad y privacidad", "alinear políticas, procesos y controles con el modelo institucional de seguridad y privacidad", "política aprobada, matriz de riesgos, controles, responsables y evidencias de cumplimiento", "aplicar controles inconsistentes y tratar datos sin garantías suficientes"),
    FunctionProfile(3, "Dirección de proyectos TI", "Ejecución y seguimiento de proyectos", "replanificar alcance, cronograma, riesgos, recursos y entregables con responsables", "línea base, tablero de avance, riesgos, actas y criterios de aceptación", "ocultar desviaciones hasta comprometer presupuesto, plazo y valor esperado"),
    FunctionProfile(4, "Desarrollo de sistemas", "Ciclo de vida de sistemas de información", "gestionar requisitos, diseño, construcción, pruebas, transición y aceptación", "trazabilidad requisito-prueba, resultados de calidad, aceptación y plan de despliegue", "liberar software que no satisface la necesidad o afecta servicios existentes"),
    FunctionProfile(5, "Analítica y soluciones de información", "Soluciones de gestión y análisis de información", "definir caso de uso, decisiones, datos, calidad, usuarios y métricas de valor", "ficha del caso, catálogo de datos e indicadores, reglas de calidad y validación usuaria", "producir análisis atractivos pero no confiables para la toma de decisiones"),
    FunctionProfile(6, "Innovación tecnológica", "Evaluación de tecnologías emergentes", "realizar un piloto controlado con criterios de valor, riesgo, interoperabilidad y salida", "informe de vigilancia, hipótesis, métricas del piloto, riesgos y recomendación", "adoptar una moda tecnológica costosa, opaca o incompatible"),
    FunctionProfile(7, "Interoperabilidad", "Intercambio seguro de información", "acordar propósito, datos mínimos, estándares, responsabilidades, seguridad y pruebas", "acuerdo de intercambio, modelo de datos, especificación de interfaz y resultados de pruebas", "generar inconsistencias, accesos indebidos o integraciones imposibles de auditar"),
    FunctionProfile(8, "Gestión de activos TI", "Documentación, configuración, código y catálogo", "centralizar activos, versionarlos, asignar responsables y probar su recuperación", "inventario, repositorios institucionales, versiones, manuales y prueba reproducible", "perder conocimiento, control del código o continuidad al cambiar personal o proveedor"),
    FunctionProfile(9, "Gestión de cambios", "Control de cambios de servicios tecnológicos", "evaluar impacto, aprobar, probar, programar, comunicar y preparar reversión", "registro de cambio, análisis, pruebas, aprobaciones, reversión y revisión posterior", "provocar indisponibilidad o introducir fallas sin trazabilidad ni recuperación"),
    FunctionProfile(10, "Evaluación de seguridad", "Pruebas y tratamiento de vulnerabilidades", "valorar hallazgos, priorizar tratamiento, corregir y volver a probar antes de aceptar riesgo residual", "informe técnico, plan de tratamiento, nueva prueba y aceptación autorizada", "liberar vulnerabilidades explotables o aceptar riesgos sin autoridad"),
    FunctionProfile(11, "Ingeniería de requisitos", "Definición funcional y tecnológica", "elicitar, priorizar, validar y mantener trazabilidad de requisitos y criterios de aceptación", "catálogo priorizado, modelos, trazabilidad, prototipos y aceptación de interesados", "ampliar alcance y recibir soluciones ambiguas o no verificables"),
    FunctionProfile(12, "Administración de datos", "Gestión de bases de datos", "diagnosticar con métricas, probar cambios, validar respaldo y programar intervención", "línea base, plan de pruebas, respaldo restaurable, cambio aprobado y medición posterior", "perder datos o degradar rendimiento sin identificar ni revertir la causa"),
    FunctionProfile(13, "Arquitectura tecnológica", "Arquitectura de software, tecnología y datos", "caracterizar arquitectura actual, definir objetivo, brechas, transición y principios", "catálogos, modelos actual y objetivo, decisiones, brechas y hoja de ruta", "crear silos, duplicidades, deuda técnica y dependencias no gestionadas"),
    FunctionProfile(14, "Contratación de tecnología", "Estudios y documentos de adquisición TI", "formular necesidad funcional, analizar alternativas, mercado, riesgos y costo de ciclo de vida", "estudio del sector, alternativas, requisitos verificables, riesgos y presupuesto", "direccionar especificaciones o adquirir una solución dependiente e inadecuada"),
    FunctionProfile(15, "Supervisión contractual", "Seguimiento de contratos TI", "contrastar entregables y niveles de servicio con evidencia antes de aceptar o pagar", "informes validados, tickets, actas, métricas, requerimientos y soporte de pago", "certificar cumplimiento inexistente y debilitar las acciones contractuales"),
    FunctionProfile(16, "Responsabilidad profesional", "Funciones asignadas y límites del empleo", "confirmar competencia, alcance, autoridad, prioridad y relación con el empleo antes de actuar", "asignación formal, alcance, responsables, entregable y criterio de cierre", "asumir decisiones sin autoridad o desatender responsabilidades prioritarias"),
)


BEHAVIORAL = (
    ("Orientación a resultados", "un hito crítico se retrasa y dos equipos se culpan", "acordar causas verificables, responsables, acciones y seguimiento"),
    ("Trabajo en equipo", "arquitectura y desarrollo defienden alternativas incompatibles", "facilitar criterios comunes, escuchar evidencia y construir una decisión documentada"),
    ("Comunicación efectiva", "la dirección necesita decidir con información técnica compleja", "traducir impactos, opciones, riesgos y recomendación en lenguaje claro"),
    ("Adaptación al cambio", "una prioridad institucional modifica el plan aprobado", "evaluar impacto, repriorizar con gobierno y comunicar la transición"),
    ("Orientación al usuario", "usuarios reportan que una solución cumple requisitos pero dificulta el servicio", "observar el uso, validar necesidades y ajustar con criterios de valor"),
    ("Aprendizaje continuo", "el equipo desconoce una tecnología necesaria para el proyecto", "identificar brechas, aprender con un piloto y compartir el conocimiento"),
    ("Toma de decisiones", "hay presión por elegir una opción sin evidencia suficiente", "definir criterios, conseguir datos mínimos y documentar supuestos y riesgos"),
    ("Iniciativa", "un riesgo recurrente no tiene responsable formal", "proponer tratamiento, responsable y seguimiento sin exceder la autoridad"),
    ("Manejo de conflictos", "un desacuerdo personal bloquea una entrega", "centrar la conversación en hechos, intereses, compromisos y escalamiento proporcional"),
    ("Compromiso institucional", "una solución local rápida contradice la arquitectura institucional", "priorizar el interés institucional y plantear una transición viable"),
    ("Aporte técnico-profesional", "se solicita avalar un diseño que no ha sido evaluado", "emitir concepto sustentado, límites, riesgos y condiciones de aprobación"),
)


INTEGRITY = (
    ("Honestidad", "un proveedor ofrece un beneficio personal antes de una evaluación", "rechazarlo, documentar y reportar por el canal definido"),
    ("Respeto", "un integrante es descalificado durante una reunión técnica", "detener la descalificación y restablecer un diálogo basado en argumentos"),
    ("Compromiso", "una falla amenaza la continuidad fuera del horario habitual", "activar el procedimiento, informar y colaborar dentro de las responsabilidades"),
    ("Diligencia", "se propone aprobar un entregable sin revisar evidencias", "realizar la verificación definida y registrar hallazgos antes de aceptar"),
    ("Justicia", "dos proveedores deben evaluarse con criterios que cambiaron durante el proceso", "aplicar criterios objetivos, transparentes e iguales conforme al procedimiento"),
    ("Conflicto de intereses", "un evaluador descubre vínculo cercano con un oferente", "declarar el conflicto y apartarse según el procedimiento"),
    ("Reserva de información", "un tercero solicita datos técnicos sensibles sin autorización", "verificar finalidad y autorización, aplicar mínimo acceso y dejar trazabilidad"),
    ("Uso de recursos públicos", "se pide usar infraestructura institucional para un proyecto particular", "negar el uso y proteger los recursos conforme a su finalidad pública"),
    ("Transparencia contractual", "el supervisor recibe presión para ocultar un incumplimiento", "registrar la evidencia y aplicar las actuaciones contractuales correspondientes"),
    ("Responsabilidad", "un error propio afectó un despliegue y aún no ha sido detectado", "informarlo oportunamente, contenerlo y contribuir a la corrección y aprendizaje"),
    ("Protección del interés general", "una solución rápida beneficia a un área pero eleva el riesgo institucional", "evaluar el impacto integral y priorizar la alternativa que proteja a la entidad y usuarios"),
)


def _rotate_options(correct: str, distractors: tuple[str, str], seed: int):
    values = [correct, *distractors]
    shift = seed % 3
    values = values[shift:] + values[:shift]
    options = dict(zip(("A", "B", "C"), values))
    correct_key = next(key for key, value in options.items() if value == correct)
    return options, correct_key


def build_adres_practice_questions() -> list[dict]:
    questions = []
    for profile in FUNCTION_PROFILES:
        variants = (
            (1, f"La dependencia inicia una actividad de {profile.topic.lower()} sin controles definidos. ¿Cuál es el primer paso más adecuado?", profile.action.capitalize() + ".", ("Ejecutar de inmediato y documentar al final.", "Delegar la decisión completa al proveedor."), "El nivel básico reconoce el control esencial antes de ejecutar."),
            (2, f"Durante el seguimiento de {profile.topic.lower()}, el responsable afirma que todo está controlado. ¿Qué evidencia permite verificarlo mejor?", profile.evidence.capitalize() + ".", ("Una confirmación verbal sin soportes.", "Una presentación comercial preparada por el proveedor."), "El nivel intermedio exige seleccionar evidencia verificable y trazable."),
            (3, f"La dirección propone omitir controles de {profile.topic.lower()} para cumplir una fecha. ¿Qué riesgo debe sustentar la recomendación técnica?", profile.risk.capitalize() + ".", ("Generar evidencia suficiente para auditoría.", "Incrementar la participación de responsables institucionales."), "El nivel avanzado integra impacto, riesgo y deber de recomendación profesional."),
        )
        for difficulty, stem, correct, distractors, rationale in variants:
            options, correct_key = _rotate_options(correct, distractors, profile.number + difficulty)
            questions.append({
                "track": "FUNCIONAL", "competency": profile.competency,
                "topic": f"F{profile.number:02d} · {profile.topic}", "difficulty": difficulty,
                "stem": stem, "options": options, "correct_key": correct_key,
                "rationale": rationale, "source_refs": f"{SOURCE_VERSION} · Función {profile.number}",
                "function_number": profile.number,
            })
    for index, (competency, situation, action) in enumerate(BEHAVIORAL, start=1):
        difficulty = 1 + (index - 1) % 3
        correct = action.capitalize() + "."
        options, correct_key = _rotate_options(correct, ("Evitar intervenir hasta que el problema desaparezca.", "Imponer una respuesta sin escuchar ni documentar."), index)
        questions.append({"track": "COMPORTAMENTAL", "competency": competency, "topic": f"Comportamental · {competency}", "difficulty": difficulty, "stem": f"En el equipo de la OPEC 252097, {situation}. ¿Cuál actuación es más efectiva?", "options": options, "correct_key": correct_key, "rationale": f"La actuación desarrolla {competency.lower()} con evidencia y responsabilidad.", "source_refs": SOURCE_VERSION, "function_number": None})
    for index, (competency, situation, action) in enumerate(INTEGRITY, start=1):
        difficulty = 1 + (index - 1) % 3
        correct = action.capitalize() + "."
        options, correct_key = _rotate_options(correct, ("Aceptar si parece producir un resultado favorable.", "Continuar sin registrar ni comunicar la situación."), index + 1)
        questions.append({"track": "COMPORTAMENTAL", "competency": f"Integridad · {competency}", "topic": f"Integridad · {competency}", "difficulty": difficulty, "stem": f"En una actuación asociada a la OPEC 252097, {situation}. ¿Qué debe hacer el servidor público?", "options": options, "correct_key": correct_key, "rationale": f"La respuesta protege el valor de {competency.lower()} y deja trazabilidad.", "source_refs": SOURCE_VERSION, "function_number": None})
    return questions
