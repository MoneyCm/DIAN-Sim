"""Banco progresivo local y reutilizable para cualquier ficha OPEC."""

import re

from core.question_banks.adres_practice import BEHAVIORAL, INTEGRITY, _rotate_options


BANK_VERSION = "banco progresivo universal v1"

_DOMAINS = (
    (("seguridad", "privacidad", "vulnerab"), "Seguridad y privacidad", "definir riesgos, controles, responsables y evidencias", "matriz de riesgos, controles aplicados y resultados de verificación", "aceptar exposiciones sin tratamiento ni autoridad"),
    (("arquitectura",), "Arquitectura empresarial", "caracterizar el estado actual, definir el objetivo, las brechas y la transición", "modelos actual y objetivo, decisiones y hoja de ruta", "crear silos, duplicidades y deuda no gestionada"),
    (("requisito", "requerimiento"), "Ingeniería de requisitos", "elicitar, priorizar, validar y trazar requisitos y criterios de aceptación", "catálogo priorizado, trazabilidad y aceptación de interesados", "ampliar el alcance y recibir resultados no verificables"),
    (("software", "sistema de informacion", "sistemas de informacion", "desarrollo"), "Sistemas de información", "gestionar requisitos, diseño, construcción, pruebas, transición y aceptación", "trazabilidad, resultados de pruebas y acta de aceptación", "liberar una solución que no satisface la necesidad"),
    (("dato", "informacion", "análisis", "analisis"), "Gestión de información y datos", "definir finalidad, datos, calidad, responsables, acceso e indicadores", "catálogo, reglas de calidad, controles e indicadores validados", "tomar decisiones con información incompleta o no confiable"),
    (("proyecto", "programa", "plan ", "planes "), "Planeación y gestión de proyectos", "definir alcance, responsables, recursos, riesgos, hitos e indicadores", "plan aprobado, matriz de responsabilidades, riesgos y tablero de avance", "ejecutar sin prioridades, responsables ni control comparable"),
    (("meta", "indicador", "seguimiento", "semafor"), "Seguimiento y evaluación", "establecer línea base, metas, indicadores, responsables y acciones correctivas", "fichas de indicadores, soportes, tablero y plan de mejora", "reportar cumplimiento sin evidencia o reaccionar demasiado tarde"),
    (("inversion", "presupuesto", "recurso"), "Planeación de inversiones", "priorizar necesidades y vincular recursos, productos, metas y resultados", "plan de inversiones, criterios de priorización y seguimiento financiero", "asignar recursos sin coherencia con las metas institucionales"),
    (("contrato", "proveedor", "supervisi"), "Contratación y supervisión", "definir entregables verificables, riesgos, niveles de servicio y seguimiento", "estudios, informes, actas, métricas y soportes de aceptación", "certificar obligaciones sin evidencia suficiente"),
    (("coordina", "grupo de trabajo", "equipo"), "Coordinación de equipos", "acordar objetivos, roles, entregables, dependencias y seguimiento", "plan de trabajo, responsables, compromisos y evidencias de avance", "duplicar esfuerzos y dejar decisiones o tareas sin responsable"),
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def classify_function(function_text: str) -> tuple[str, str, str, str]:
    normalized = _clean(function_text).casefold()
    for keywords, competency, action, evidence, risk in _DOMAINS:
        if any(keyword in normalized for keyword in keywords):
            return competency, action, evidence, risk
    return (
        "Gestión técnica del empleo",
        "precisar la finalidad, el alcance, la autoridad, los responsables y el resultado esperado",
        "asignación, procedimiento aplicable, producto verificable y registro de cierre",
        "actuar sin competencia, trazabilidad o alineación con la necesidad institucional",
    )


def build_opec_progressive_questions(opec, competition_code: str = "") -> list[dict]:
    functions = [_clean(item) for item in (getattr(opec, "functions", None) or []) if _clean(item)]
    if not functions:
        functions = [_clean(getattr(opec, "purpose", "Gestión de las responsabilidades del empleo"))]
    opec_number = _clean(getattr(opec, "opec_number", "sin número"))
    job_title = _clean(getattr(opec, "job_title", "empleo público"))
    source = f"OPEC {opec_number} · {BANK_VERSION} · guía oficial pendiente"
    functional_target = min(60, max(48, len(functions) * 3))
    questions = []
    for index in range(functional_target):
        number = index % len(functions) + 1
        difficulty = index // len(functions) % 3 + 1
        function_text = functions[number - 1]
        competency, action, evidence, risk = classify_function(function_text)
        variants = {
            1: (f"Antes de ejecutar la función {number} de la OPEC {opec_number}, ¿cuál es el primer paso más adecuado?", action, ("Ejecutar de inmediato y documentar solamente al final", "Trasladar toda la decisión a un tercero"), "El nivel básico identifica el control esencial antes de actuar."),
            2: (f"Durante el seguimiento de la función {number}, ¿qué evidencia permite verificar mejor su cumplimiento?", evidence, ("Una confirmación verbal sin soportes", "Una presentación general que no demuestra el resultado"), "El nivel intermedio exige evidencia verificable y trazable."),
            3: (f"Se propone omitir controles para acelerar la función {number}. ¿Qué riesgo debe sustentar la recomendación profesional?", risk, ("Producir evidencia suficiente para la evaluación", "Aumentar la claridad sobre los responsables"), "El nivel avanzado integra impacto, riesgo y responsabilidad profesional."),
        }
        stem, correct, distractors, rationale = variants[difficulty]
        options, correct_key = _rotate_options(correct.capitalize() + ".", tuple(x + "." for x in distractors), index)
        questions.append({"track": "FUNCIONAL", "competency": competency, "topic": f"F{number:02d} · {competency}", "difficulty": difficulty, "stem": stem, "options": options, "correct_key": correct_key, "rationale": rationale, "source_refs": f"{source} · Función {number}: {function_text[:240]}", "function_number": number})

    for index, (competency, situation, action) in enumerate(BEHAVIORAL, start=1):
        difficulty = 1 + (index - 1) % 3
        correct = action.capitalize() + "."
        options, correct_key = _rotate_options(correct, ("Evitar intervenir hasta que el problema desaparezca.", "Imponer una respuesta sin escuchar ni documentar."), index)
        questions.append({"track": "COMPORTAMENTAL", "competency": competency, "topic": f"Comportamental · {competency}", "difficulty": difficulty, "stem": f"En el cargo {job_title}, {situation}. ¿Cuál actuación es más efectiva?", "options": options, "correct_key": correct_key, "rationale": f"La actuación desarrolla {competency.lower()} con evidencia y responsabilidad.", "source_refs": source, "function_number": None})
    for index, (competency, situation, action) in enumerate(INTEGRITY, start=1):
        difficulty = 1 + (index - 1) % 3
        correct = action.capitalize() + "."
        options, correct_key = _rotate_options(correct, ("Aceptar si parece producir un resultado favorable.", "Continuar sin registrar ni comunicar la situación."), index + 1)
        questions.append({"track": "COMPORTAMENTAL", "competency": f"Integridad · {competency}", "topic": f"Integridad · {competency}", "difficulty": difficulty, "stem": f"En una actuación de la OPEC {opec_number}, {situation}. ¿Qué debe hacer el servidor público?", "options": options, "correct_key": correct_key, "rationale": f"La respuesta protege el valor de {competency.lower()} y deja trazabilidad.", "source_refs": source, "function_number": None})
    return questions


def build_progressive_bank(opec, competition_code: str = "") -> list[dict]:
    if competition_code == "ADRES-ABIERTO" and str(getattr(opec, "opec_number", "")) == "252097":
        from core.question_banks.adres_practice import build_adres_practice_questions
        return build_adres_practice_questions()
    return build_opec_progressive_questions(opec, competition_code)
