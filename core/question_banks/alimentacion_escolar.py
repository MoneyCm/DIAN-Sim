"""Banco curado para el empleo TI de la UApA (Proceso de Selección 2727)."""

from __future__ import annotations

import hashlib
import uuid

from db.models import Question


COMPETITION_CODE = "ALIMENTACION-ESCOLAR-ABIERTO"
TARGET_COUNT = 100

PETI = "UApA, Plan Estratégico de Tecnologías de Información (PETI) 2024-2026, versión 2026"
MRAE = "MinTIC, Marco de Referencia de Arquitectura Empresarial (MRAE)"
FICHA = "Ficha del empleo UApA, Subdirección de Información, suministrada por el aspirante"


SCENARIOS = [
    ("Alineación PETI", "Una dependencia solicita una solución urgente que no aparece relacionada con objetivos institucionales ni con el PETI.", "Trazar la necesidad con objetivos, capacidades, iniciativas y hoja de ruta antes de priorizarla.", "Matriz de alineación entre necesidad, objetivo institucional, iniciativa PETI, responsable, costo y resultado.", "Porcentaje de iniciativas TI con trazabilidad completa al PETI.", "Invertir en soluciones aisladas que no generan valor institucional.", PETI),
    ("Arquitectura empresarial", "Cada área compra tecnología de forma independiente y aparecen soluciones duplicadas.", "Levantar la arquitectura actual, definir la arquitectura objetivo y cerrar brechas mediante una hoja de ruta gobernada.", "Catálogos, modelos de arquitectura actual y objetivo, análisis de brechas y hoja de ruta aprobada.", "Porcentaje de brechas de arquitectura cerradas según la hoja de ruta.", "Aumentar duplicidades, costos de integración y deuda tecnológica.", MRAE),
    ("Dominio institucional", "El equipo comienza a diseñar una aplicación sin comprender procesos, actores ni capacidades institucionales.", "Modelar primero la estrategia, capacidades y procesos que la solución debe habilitar.", "Mapa de capacidades y procesos vinculado con objetivos y necesidades de los grupos de valor.", "Porcentaje de requisitos asociados a procesos y capacidades institucionales.", "Automatizar ineficiencias o construir funciones que no responden a la misión.", MRAE),
    ("Arquitectura de información", "Dos sistemas reportan cifras distintas para el mismo beneficiario del PAE.", "Definir gobierno, responsables, reglas de calidad, modelo e intercambio del dato antes de conciliar reportes.", "Diccionario de datos, reglas de calidad, linaje, responsables y resultados de conciliación.", "Porcentaje de datos críticos que cumplen reglas de calidad.", "Tomar decisiones con información inconsistente y sin trazabilidad.", MRAE),
    ("Sistemas de información", "Se propone reemplazar un sistema sin inventario de funcionalidades, integraciones o usuarios.", "Caracterizar el sistema y sus dependencias, evaluar brechas y diseñar la transición con continuidad.", "Catálogo del sistema, integraciones, usuarios, criticidad, costos y plan de transición.", "Porcentaje de sistemas caracterizados y con ciclo de vida definido.", "Interrumpir servicios o perder integraciones y datos necesarios.", MRAE),
    ("Servicios tecnológicos", "Un servicio crítico presenta fallas recurrentes y solo se atiende cuando un usuario se queja.", "Gestionar incidentes y problemas, analizar causa raíz, acordar niveles de servicio y aplicar acciones preventivas.", "Tickets, análisis de causa raíz, historial de cambios y reporte de niveles de servicio.", "Disponibilidad del servicio y tiempo medio de restauración.", "Normalizar fallas repetitivas y afectar la continuidad operativa.", PETI),
    ("Mesa de servicio", "Una solicitud llega por mensajes personales y no queda registro de atención.", "Radicarla en la mesa de servicio, clasificarla, priorizarla, asignarla y cerrar con evidencia y satisfacción.", "Ticket de Aranda con categoría, prioridad, responsable, tiempos, solución y cierre.", "Porcentaje de solicitudes atendidas dentro del nivel de servicio.", "Perder trazabilidad, prioridad y medición de la atención.", PETI),
    ("Ecosistema SiPAE", "Un área plantea crear otra aplicación para una función ya cubierta dentro del ecosistema SiPAE.", "Verificar primero las capacidades de SigePAE, MiPAE, PAEstar al día y PAE a la mano, y evaluar integración o evolución.", "Mapa de capacidades del ecosistema y análisis de brecha funcional.", "Porcentaje de necesidades resueltas reutilizando o evolucionando capacidades existentes.", "Duplicar datos, experiencia y costos de operación.", PETI),
    ("Desarrollo seguro", "El equipo deja las pruebas de seguridad para el día anterior a producción.", "Integrar requisitos, análisis, pruebas y correcciones de seguridad durante todo el ciclo de desarrollo.", "Requisitos de seguridad, análisis de código, pruebas, hallazgos y aceptación de riesgos.", "Porcentaje de vulnerabilidades críticas corregidas antes del despliegue.", "Liberar vulnerabilidades costosas de corregir y exponer información institucional.", PETI),
    ("Calidad de software", "Una solución funciona hoy, pero cada cambio tarda meses y el crecimiento degrada el servicio.", "Incorporar atributos medibles de modificabilidad, escalabilidad, seguridad y privacidad en la arquitectura y aceptación.", "Escenarios de calidad, pruebas de carga y criterios de aceptación no funcionales.", "Tiempo de cambio y capacidad soportada dentro de los umbrales acordados.", "Acumular deuda técnica y limitar la evolución del servicio.", PETI),
    ("Seguridad y privacidad", "Un proyecto maneja datos personales y solo considera controles al finalizar la construcción.", "Aplicar privacidad y seguridad desde el diseño, identificar riesgos, tratamiento, controles y responsables.", "Inventario y clasificación de activos, análisis de riesgos, controles y evaluación de privacidad.", "Porcentaje de riesgos altos tratados antes de producción.", "Vulnerar confidencialidad, integridad, disponibilidad o derechos de los titulares.", PETI),
    ("Gestión de activos", "La entidad desconoce quién es responsable de una base de datos crítica.", "Inventariar y clasificar el activo, asignar propietario y custodio, y definir controles según su criticidad.", "Inventario actualizado con clasificación, propietario, custodio y tratamiento.", "Porcentaje de activos críticos con responsable y controles definidos.", "Dejar datos críticos sin decisiones claras de protección y uso.", PETI),
    ("Gestión de incidentes", "Se detecta acceso anómalo a información sensible y el equipo intenta borrarlo sin registrar el evento.", "Contener, preservar evidencia, escalar por el procedimiento, analizar impacto, recuperar y documentar lecciones.", "Registro cronológico, evidencias, alcance, acciones, comunicaciones y cierre del incidente.", "Tiempo medio de detección y contención de incidentes.", "Perder evidencia, repetir la causa y agravar el impacto.", PETI),
    ("Continuidad", "Un sistema esencial depende de un único servidor y nunca se ha probado su recuperación.", "Realizar análisis de impacto, definir objetivos de recuperación, redundancia, copias y pruebas periódicas.", "BIA, RTO/RPO aprobados y resultados de pruebas de restauración y continuidad.", "Porcentaje de servicios críticos recuperados dentro del RTO y RPO.", "Descubrir durante la contingencia que las copias o procedimientos no funcionan.", PETI),
    ("ISO 27001:2022", "Un equipo trata la migración a ISO 27001:2022 como una lista documental sin relación con los riesgos.", "Gestionarla como un sistema basado en contexto, riesgos, controles, seguimiento y mejora continua.", "Alcance, evaluación de riesgos, plan de tratamiento, controles, auditorías e indicadores.", "Porcentaje de acciones del plan de tratamiento cerradas eficazmente.", "Obtener documentos sin reducir la exposición real de la entidad.", PETI),
    ("Analítica de datos", "La dirección pide un tablero, pero no existe una pregunta de decisión ni datos validados.", "Definir primero el caso de uso, decisión, usuarios, indicadores, fuentes, calidad y reglas de interpretación.", "Ficha del caso analítico, catálogo de indicadores, reglas de calidad y validación con usuarios.", "Porcentaje de indicadores del tablero con fuente y fórmula certificadas.", "Producir visualizaciones atractivas que induzcan decisiones equivocadas.", PETI),
    ("Gestión de proyectos TI", "Un proyecto inicia desarrollo sin alcance, entregables, riesgos ni criterios de aceptación.", "Formalizar gobierno, alcance, cronograma, costos, riesgos, calidad, cambios y aceptación antes de ejecutar.", "Acta, EDT o backlog, cronograma, matriz de riesgos y criterios de aceptación.", "Porcentaje de entregables aceptados en plazo, costo y calidad acordados.", "Generar reprocesos, sobrecostos y disputas sobre lo que debía entregarse.", FICHA),
    ("Proveedores TI", "Un proveedor reporta avance por horas trabajadas, aunque los entregables no funcionan.", "Controlar resultados mediante entregables verificables, niveles de servicio, seguridad, conocimiento y aceptación.", "Informes de pruebas, actas de aceptación, SLA, hallazgos y plan de transferencia.", "Porcentaje de entregables aceptados sin defectos críticos.", "Pagar actividad sin recibir capacidad operativa ni conocimiento sostenible.", FICHA),
    ("Adopción tecnológica", "Se propone adoptar una tecnología de moda sin caso de uso ni evaluación de riesgos.", "Ejecutar vigilancia, caso de negocio y piloto controlado con criterios de valor, interoperabilidad, costo, seguridad y salida.", "Matriz comparativa, concepto de arquitectura y resultados medibles del piloto.", "Porcentaje de pilotos que demuestran valor antes de escalar.", "Crear dependencia tecnológica y costos sin beneficio comprobado.", FICHA),
    ("Uso y apropiación", "Se despliega una nueva herramienta, pero los usuarios continúan usando hojas personales.", "Caracterizar actores y brechas, gestionar el cambio, formar por roles, acompañar y medir adopción efectiva.", "Plan de apropiación, materiales, asistencia, retroalimentación y métricas de uso.", "Porcentaje de usuarios objetivo activos y procesos ejecutados en la herramienta.", "Confundir instalación con transformación y no obtener los beneficios esperados.", PETI),
]


def _options(correct: str, wrong_1: str, wrong_2: str, offset: int):
    letters = ("A", "B", "C")
    values = [correct, wrong_1, wrong_2]
    values = values[offset:] + values[:offset]
    return dict(zip(letters, values)), letters[values.index(correct)]


def build_questions():
    """Construye 100 ítems situacionales: cinco por cada uno de 20 dominios."""
    rows = []
    for scenario_index, (domain, situation, action, evidence, indicator, risk, source) in enumerate(SCENARIOS):
        prompts = [
            (f"{situation} ¿Cuál es la actuación profesional más adecuada?", action,
             "Comprar o desarrollar de inmediato para mostrar avance, sin análisis adicional.",
             "Cerrar la solicitud porque documentarla retrasaría la ejecución.",
             f"La decisión adecuada es {action.lower()}"),
            (f"En el caso de {domain.lower()}, ¿qué evidencia sustenta mejor una decisión verificable?", evidence,
             "Una conversación informal sin fecha, responsable ni fuente.",
             "Una presentación comercial sin criterios de evaluación.",
             f"La evidencia pertinente es: {evidence}"),
            (f"¿Qué indicador permite seguir mejor la gestión de {domain.lower()}?", indicator,
             "Número de correos enviados por el equipo.",
             "Cantidad de diapositivas presentadas en el comité.",
             f"Este indicador mide directamente el desempeño esperado: {indicator}"),
            (f"¿Cuál es el riesgo principal de no corregir la situación de {domain.lower()}?", risk,
             "Que el presupuesto aumente automáticamente.",
             "Que todos los usuarios adopten la solución sin acompañamiento.",
             f"El riesgo relevante es {risk.lower()}"),
            (f"Frente a {domain.lower()}, ¿qué enfoque debe orientar primero la respuesta del empleo?", action,
             "Delegar toda la decisión al proveedor, aunque la responsabilidad siga siendo institucional.",
             "Elegir la alternativa más rápida sin conservar evidencia ni evaluar impactos.",
             f"La función exige gestión especializada y trazable; por eso corresponde {action.lower()}"),
        ]
        for prompt_index, (stem, correct, wrong_1, wrong_2, rationale) in enumerate(prompts):
            options, key = _options(correct, wrong_1, wrong_2, (scenario_index + prompt_index) % 3)
            rows.append({"domain": domain, "stem": stem, "options": options, "correct": key,
                         "rationale": rationale, "source": source})
    return rows


def seed_questions(db, competition_id: int) -> int:
    """Inserta el banco de forma idempotente y devuelve cuántas filas creó."""
    created = 0
    for row in build_questions():
        digest = hashlib.sha256(f"{COMPETITION_CODE}|{row['stem']}".encode("utf-8")).hexdigest()
        exists = db.query(Question).filter(
            (Question.competition_id == competition_id) &
            ((Question.hash_norm == digest) | (Question.stem == row["stem"]))
        ).first()
        if exists:
            continue
        db.add(Question(
            competition_id=competition_id,
            question_id=str(uuid.uuid4()),
            track="FUNCIONAL",
            competency="Gestión de tecnologías de la información",
            topic=f"UApA - {row['domain']}",
            macro_dominio="Arquitectura y gestión de TI",
            micro_competencia=row["domain"],
            difficulty=2,
            question_type="SITUATIONAL",
            stem=row["stem"],
            options_json=row["options"],
            correct_key=row["correct"],
            rationale=row["rationale"],
            source_refs=row["source"],
            hash_norm=digest,
            is_verified=True,
        ))
        created += 1
    db.commit()
    return created
