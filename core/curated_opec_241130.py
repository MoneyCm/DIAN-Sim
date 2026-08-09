"""Reviewed GOA-style cases for Territorial 12, OPEC 241130."""

from __future__ import annotations


COMPETITION_CODE = "TERRITORIAL-12-BOLIVAR-2685"
OPEC_NUMBER = "241130"
SOURCE_URL = "https://www.cnsc.gov.co/node/55042"
SOURCE_VERSION = "cnsc-2025-11-27"


CASE_SPECS = (
    {
        "id": "goa-241130-f1-grupo-permanente-01",
        "function": 1,
        "topic": "Coordinación de grupos permanentes",
        "difficulty": 2,
        "text": "La Secretaría de Educación solicita al Profesional Especializado coordinar un grupo permanente que hará seguimiento al Plan Departamental de Desarrollo. El acto administrativo existe, pero no se ha socializado con todos los integrantes ni se han definido entregables.",
        "action": "Verificar el acto administrativo y acordar con los integrantes un plan de trabajo, responsabilidades, entregables y cronograma dentro de su alcance.",
        "evidence": "Acto administrativo vigente, acta de instalación y plan de trabajo con responsables y fechas.",
        "risk": "Impartir instrucciones sin alcance definido y perder trazabilidad de los compromisos del grupo.",
    },
    {
        "id": "goa-241130-f2-grupo-temporal-01",
        "function": 2,
        "topic": "Coordinación de grupos temporales",
        "difficulty": 2,
        "text": "Para formular un proyecto educativo se conformó un grupo temporal con tareas similares asignadas por dos dependencias. Los avances no son comparables y hay actividades duplicadas.",
        "action": "Solicitar lineamientos al superior inmediato y consolidar un plan temporal con objetivo, productos, responsables y canal de decisiones.",
        "evidence": "Instrucción del superior y matriz de responsabilidades aprobada por el grupo temporal.",
        "risk": "Duplicar actividades, incumplir plazos y presentar productos incompatibles.",
    },
    {
        "id": "goa-241130-f3-revision-estrategica-01",
        "function": 3,
        "topic": "Revisión estratégica y normativa",
        "difficulty": 3,
        "text": "Una propuesta sectorial promete resolver una brecha educativa, pero el documento no relaciona la competencia departamental, las normas aplicables ni la evidencia que sustenta el problema.",
        "action": "Revisar competencia, marco normativo, evidencia del problema y coherencia de la alternativa antes de emitir concepto técnico.",
        "evidence": "Matriz normativa y análisis técnico que relacione problema, competencia, alternativa y restricciones.",
        "risk": "Aprobar una intervención inviable o contraria a las competencias de la entidad.",
    },
    {
        "id": "goa-241130-f4-plan-inversiones-01",
        "function": 4,
        "topic": "Plan de inversiones educativo",
        "difficulty": 3,
        "text": "Cinco proyectos compiten por recursos del Plan de Desarrollo Educativo. Dos tienen mayor impacto esperado, pero uno de los restantes recibió una solicitud informal de priorización.",
        "action": "Aplicar criterios documentados de alineación estratégica, impacto, viabilidad, población beneficiaria, costo y urgencia para recomendar la priorización.",
        "evidence": "Matriz de priorización con criterios, ponderaciones, puntajes y justificación de la recomendación.",
        "risk": "Asignar recursos por presión informal en lugar de la contribución verificable al plan.",
    },
    {
        "id": "goa-241130-f5-poai-01",
        "function": 5,
        "topic": "Plan indicativo y POAI",
        "difficulty": 3,
        "text": "El equipo debe elaborar el plan indicativo, planes de acción y POAI. Las metas anuales fueron copiadas del plan de desarrollo, pero no tienen responsables, recursos ni hitos.",
        "action": "Desagregar las metas en productos, responsables, recursos, hitos e indicadores consistentes con el plan de desarrollo y la distribución presupuestal.",
        "evidence": "POAI y planes de acción con metas anuales, responsables, recursos, cronograma e indicadores trazables.",
        "risk": "Tener planes declarativos que no permitan ejecutar ni hacer seguimiento a las metas.",
    },
    {
        "id": "goa-241130-f6-formulacion-informacion-01",
        "function": 6,
        "topic": "Formulación de proyectos",
        "difficulty": 2,
        "text": "Para formular un programa de permanencia escolar se recibieron cifras de matrícula de varias fuentes, con periodos y definiciones diferentes.",
        "action": "Definir la información requerida, validar fuente, periodo, cobertura y consistencia antes de usarla en la formulación.",
        "evidence": "Ficha de datos con fuente, fecha de corte, definición, responsable de validación y limitaciones de uso.",
        "risk": "Formular el programa con una línea base inconsistente y estimar de forma errónea la necesidad.",
    },
    {
        "id": "goa-241130-f7-indicadores-01",
        "function": 7,
        "topic": "Indicadores de cumplimiento",
        "difficulty": 3,
        "text": "Un informe reporta 95% de ejecución presupuestal y concluye que la meta de calidad educativa fue cumplida, sin mostrar resultados ni población atendida.",
        "action": "Contrastar ejecución financiera con indicadores de producto, resultado e impacto definidos para la meta y explicar las desviaciones.",
        "evidence": "Ficha del indicador con fórmula, línea base, meta, resultado, fuente y análisis de desviaciones.",
        "risk": "Confundir el gasto ejecutado con el logro efectivo de un resultado institucional.",
    },
    {
        "id": "goa-241130-f8-ajuste-poai-01",
        "function": 8,
        "topic": "Ajuste del POAI",
        "difficulty": 3,
        "text": "Un cambio en el costo de una obra educativa obliga a modificar el cronograma y la distribución de recursos del POAI. El equipo propone ejecutar el cambio primero y formalizarlo después.",
        "action": "Analizar los efectos técnicos, presupuestales y de metas, y tramitar la aprobación del ajuste ante la instancia competente antes de ejecutarlo.",
        "evidence": "Solicitud de ajuste con soportes técnicos y presupuestales, decisión de la instancia competente y versión controlada del POAI.",
        "risk": "Ejecutar cambios no autorizados, perder trazabilidad y distorsionar el seguimiento de metas.",
    },
    {
        "id": "goa-241130-f9-semaforizacion-01",
        "function": 9,
        "topic": "Semaforización de metas",
        "difficulty": 3,
        "text": "El tablero muestra una meta en verde porque los recursos se comprometieron, aunque el avance físico está retrasado y no hay evidencia de calidad del producto.",
        "action": "Definir y aplicar umbrales que integren avance físico, financiero, plazo y evidencia de calidad para clasificar la meta.",
        "evidence": "Ficha de semaforización con umbrales, fórmula, periodicidad, responsables y fuentes de verificación.",
        "risk": "Ocultar alertas reales al evaluar únicamente la ejecución presupuestal.",
    },
    {
        "id": "goa-241130-f5-poai-riesgos-02",
        "function": 5,
        "topic": "Plan indicativo y POAI",
        "difficulty": 3,
        "text": "La ejecución del POAI depende de un convenio que presenta retrasos. El plan no identificó el riesgo ni definió una medida de contingencia, y el cierre anual se aproxima.",
        "action": "Registrar el riesgo, evaluar su impacto en metas y recursos, definir acciones de contingencia y actualizar el seguimiento con los responsables.",
        "evidence": "Matriz de riesgos con causa, impacto, controles, responsable, plan de contingencia y reporte de seguimiento.",
        "risk": "Detectar el incumplimiento demasiado tarde y no contar con alternativas para proteger las metas anuales.",
    },
)


def source_ref(function_number: int) -> str:
    return (
        f"SIMO, OPEC {OPEC_NUMBER}, función {function_number}; Acuerdo CNSC No. 36 de 2025 "
        f"(Proceso 2685 - Territorial 12), arts. 1 y 13; {SOURCE_URL}; "
        f"vigencia consultada {SOURCE_VERSION}."
    )


def _options(correct: str, first_distractor: str, second_distractor: str, offset: int):
    choices = [correct, first_distractor, second_distractor]
    choices = choices[offset:] + choices[:offset]
    letters = ("A", "B", "C")
    return dict(zip(letters, choices)), letters[choices.index(correct)]


def questions_for_case(spec: dict, index: int) -> list[dict]:
    prompts = (
        (
            "¿Cuál es la actuación más adecuada del Profesional Especializado?",
            spec["action"],
            "Continuar sin verificar competencias, evidencia ni responsables para evitar retrasos.",
            "Modificar informalmente las metas y el presupuesto para que el informe no muestre alertas.",
            f"La actuación protege la trazabilidad y el cumplimiento de la función {spec['function']}.",
        ),
        (
            "¿Cuál es el soporte más útil para una decisión verificable?",
            spec["evidence"],
            "Comentarios verbales sin responsable, fecha ni fuente identificable.",
            "Una presentación sin datos de respaldo ni control de versión.",
            "El soporte permite verificar la decisión y hacer seguimiento posterior.",
        ),
        (
            "¿Cuál es el riesgo principal de no corregir la situación?",
            spec["risk"],
            "Que las metas se cumplan automáticamente sin gestionar las causas del problema.",
            "Que se incrementen los recursos sin requerir análisis ni autorización.",
            "El riesgo se deriva directamente de omitir los controles de la función asignada.",
        ),
    )
    questions = []
    for question_index, (prompt, correct, distractor_1, distractor_2, rationale) in enumerate(prompts):
        options, correct_key = _options(correct, distractor_1, distractor_2, (index + question_index) % 3)
        questions.append({
            "stem": f"{spec['text']} {prompt}",
            "options": options,
            "correct_key": correct_key,
            "rationale": rationale,
            "source_ref": source_ref(spec["function"]),
        })
    return questions
