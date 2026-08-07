"""Banco curado para el empleo TI de la UApA (Proceso de Selección 2727)."""

from __future__ import annotations

import hashlib
import uuid

from db.models import CaseStudy, Question


COMPETITION_CODE = "ALIMENTACION-ESCOLAR-ABIERTO"
TARGET_COUNT = 100
ADVANCED_CASE_COUNT = 10
ADVANCED_QUESTION_COUNT = 30

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


ADVANCED_CASES = [
    ("Integración y calidad de SiPAE", "La Subdirección de Información recibe informes contradictorios sobre beneficiarios del PAE. SigePAE conserva identificadores territoriales, una nueva solución usa documentos sin normalizar y el tablero directivo suma registros de ambas fuentes. El proveedor propone corregir manualmente el tablero antes de cada comité. No existe responsable formal del dato ni reglas documentadas de conciliación.", "Detener la publicación como dato certificado, definir responsables, identificadores maestros, reglas de calidad y linaje, y corregir la integración desde la fuente.", "Diccionario y linaje aprobados, reporte de duplicados y conciliación reproducible entre fuentes.", "Porcentaje de registros críticos únicos, completos y conciliados.", "Institucionalizar ajustes manuales que ocultan el problema y producen decisiones no reproducibles.", "Arquitectura de información", PETI),
    ("Modernización de un sistema crítico", "Un sistema misional presenta fallas, pero soporta integraciones no documentadas con varias entidades. La dirección solicita reemplazarlo en tres meses. El proveedor nuevo propone apagarlo al liberar la primera versión y migrar únicamente los datos del último año. Las áreas usuarias no han validado procesos ni criterios de aceptación.", "Caracterizar dependencias y datos, definir arquitectura de transición, migración verificable, pruebas integrales y reversión antes del retiro gradual.", "Catálogo de integraciones, plan de migración, resultados de pruebas, conciliación y plan de reversión.", "Porcentaje de integraciones y datos críticos validados antes del corte.", "Interrumpir servicios, perder información histórica y descubrir dependencias después del apagado.", "Sistemas de información", MRAE),
    ("Incidente de seguridad en producción", "La mesa de servicio recibe alertas de accesos atípicos a una base con información personal. Un administrador reinicia el servidor para recuperar rendimiento y propone borrar los registros antiguos. Aún no se conoce el alcance, no se ha informado al responsable de seguridad y el servicio continúa expuesto.", "Activar el procedimiento de incidentes: contener sin destruir evidencia, preservar registros, escalar, analizar alcance, erradicar, recuperar y documentar.", "Línea de tiempo, registros preservados, alcance, decisiones de contención y lecciones aprendidas.", "Tiempo de detección, contención y recuperación, junto con recurrencia del incidente.", "Destruir evidencia, ampliar la exposición y omitir obligaciones de gestión y comunicación.", "Seguridad y privacidad", PETI),
    ("Contratación de nube", "La entidad evalúa trasladar un servicio crítico a nube. La oferta más barata no especifica ubicación y portabilidad de datos, recuperación, salida, subcontratistas ni atención de incidentes. El área solicitante quiere adjudicar por precio y definir esos aspectos durante la ejecución.", "Evaluar riesgos y arquitectura, y exigir antes de contratar requisitos de seguridad, continuidad, niveles de servicio, portabilidad, reversibilidad y responsabilidades.", "Matriz de requisitos y riesgos, evaluación técnica, SLA y plan de salida contractual.", "Porcentaje de requisitos críticos cubiertos y probados por el proveedor.", "Crear dependencia del proveedor y carecer de recuperación, control o salida viable.", "Servicios tecnológicos y proveedores", FICHA),
    ("Tablero analítico para inspección", "Se solicita un tablero que priorice alertas para inspección y vigilancia. El prototipo usa una fórmula creada por el proveedor, mezcla datos de fechas distintas y no permite explicar por qué una entidad territorial aparece en riesgo alto. La dirección desea publicarlo por la urgencia operativa.", "Definir el propósito decisorio, validar fuentes y cortes, documentar la fórmula, probar sesgos y calidad, y habilitar trazabilidad antes del uso.", "Ficha de indicadores, versión del modelo, fuentes, pruebas de calidad y validación de usuarios responsables.", "Porcentaje de alertas trazables a datos certificados y reglas explicables.", "Orientar actuaciones con resultados opacos, desactualizados o sesgados.", "Analítica y gestión de información", FICHA),
    ("Cambio urgente de software", "Una vulnerabilidad crítica exige modificar una aplicación. El proveedor propone aplicar el cambio directamente en producción porque el ambiente de pruebas está desactualizado. No hay copia reciente verificada ni procedimiento de reversión, aunque la ventana disponible es corta.", "Contener el riesgo, actualizar una prueba representativa, verificar respaldo y reversión, probar el cambio y autorizarlo con seguimiento reforzado.", "Solicitud de cambio, evaluación de riesgo, prueba, respaldo verificado, aprobación y resultado posterior.", "Porcentaje de cambios urgentes exitosos sin incidentes ni reversión fallida.", "Convertir una corrección de seguridad en indisponibilidad o pérdida de información.", "Gestión de cambios y desarrollo seguro", PETI),
    ("Arquitectura empresarial fragmentada", "Tres áreas presentan proyectos: una aplicación móvil, una plataforma documental y un nuevo lago de datos. Todos solicitan presupuesto por separado, comparten usuarios e información, pero emplean tecnologías incompatibles. Ninguno identifica capacidades institucionales ni reutilización de servicios existentes.", "Evaluarlos como portafolio, mapear capacidades y datos compartidos, definir arquitectura objetivo, principios y hoja de ruta incremental.", "Mapa de capacidades, catálogos, arquitectura objetivo, brechas, dependencias y hoja de ruta priorizada.", "Porcentaje de iniciativas alineadas con arquitectura objetivo y componentes reutilizables.", "Financiar silos incompatibles y multiplicar costos de operación e integración.", "Arquitectura empresarial", MRAE),
    ("Continuidad del ecosistema", "Durante una interrupción de conectividad, el equipo descubre que el procedimiento de continuidad solo cubre servidores, pero no identidad, red, integraciones ni personal clave. Las copias existen, aunque nunca se han restaurado. El servicio tiene un RTO declarado sin análisis de impacto.", "Realizar análisis de impacto integral, validar dependencias, acordar RTO/RPO realistas y ejecutar pruebas de restauración y continuidad de extremo a extremo.", "BIA, mapa de dependencias y resultados de ejercicios que demuestren RTO y RPO.", "Porcentaje de servicios críticos recuperados dentro de objetivos probados.", "Confiar en copias no verificadas y planes parciales que fallan durante una contingencia real.", "Continuidad de servicios TI", PETI),
    ("Adopción de inteligencia artificial", "Un proveedor ofrece clasificar automáticamente solicitudes ciudadanas mediante IA y usar los mensajes históricos para entrenar. No explica calidad, tratamiento de datos personales, revisión humana, errores por categoría ni posibilidad de retirar la solución. Se promete reducir tiempos en 60 %.", "Delimitar caso de uso y datos, evaluar privacidad, seguridad, calidad y sesgos, diseñar supervisión humana y ejecutar un piloto con criterios de salida.", "Evaluación de impacto, conjunto de prueba, métricas por categoría, controles humanos y resultados del piloto.", "Precisión y tasa de error por categoría, con porcentaje de decisiones revisadas cuando corresponda.", "Escalar decisiones erróneas u opacas y tratar datos sin controles suficientes.", "Tecnologías emergentes", FICHA),
    ("Apropiación y valor", "Se implementó una herramienta de gestión de proyectos, pero solo el equipo TI la utiliza. Las áreas continúan enviando avances por correo porque la configuración no refleja sus flujos y la capacitación fue una demostración general. El proveedor reporta éxito porque todas las licencias fueron activadas.", "Analizar actores y brechas, ajustar flujos prioritarios, formar por rol, acompañar el cambio y medir uso efectivo y resultados.", "Línea base, plan de cambio, configuración validada, métricas de uso y retroalimentación de usuarios.", "Porcentaje de proyectos gestionados de extremo a extremo y usuarios activos por rol.", "Medir licencias en vez de adopción y mantener procesos paralelos sin beneficios institucionales.", "Uso y apropiación", PETI),
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


def build_advanced_case_questions():
    """Construye 10 casos extensos con tres preguntas avanzadas por caso."""
    cases = []
    for case_index, (title, text, action, evidence, indicator, risk, domain, source) in enumerate(ADVANCED_CASES):
        prompts = [
            ("¿Cuál debe ser la primera decisión técnica del Profesional Especializado?", action,
             "Aceptar la alternativa más rápida y documentar sus efectos cuando termine la ejecución.",
             "Trasladar toda la decisión al proveedor porque conoce la tecnología.",
             f"La respuesta integra gobierno, riesgo y trazabilidad: {action}"),
            ("¿Cuál evidencia ofrece el soporte más sólido para autorizar la actuación?", evidence,
             "Un correo que indique que el equipo está de acuerdo, sin anexos técnicos.",
             "La presentación comercial de la solución propuesta.",
             f"La decisión debe sustentarse en evidencia verificable: {evidence}"),
            ("¿Cuál indicador es más pertinente para verificar el resultado?", indicator,
             "Número de reuniones realizadas durante el proyecto.",
             "Cantidad total de mensajes enviados por el equipo.",
             f"El indicador se relaciona directamente con el resultado: {indicator}"),
        ]
        questions = []
        for prompt_index, (stem, correct, wrong_1, wrong_2, rationale) in enumerate(prompts):
            options, key = _options(correct, wrong_1, wrong_2, (case_index + prompt_index + 1) % 3)
            questions.append({"stem": stem, "options": options, "correct": key, "rationale": rationale})
        cases.append({"title": title, "text": text, "domain": domain, "source": source, "questions": questions})
    return cases


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


def seed_advanced_cases(db, competition_id: int) -> int:
    """Inserta casos avanzados y sus preguntas de forma idempotente."""
    created = 0
    for case_data in build_advanced_case_questions():
        case = db.query(CaseStudy).filter(
            CaseStudy.competition_id == competition_id,
            CaseStudy.title == case_data["title"],
        ).first()
        if case is None:
            case = CaseStudy(competition_id=competition_id, title=case_data["title"],
                             text=case_data["text"], difficulty=3, topic=case_data["domain"])
            db.add(case)
            db.flush()
        for row in case_data["questions"]:
            full_stem = f"Caso {case_data['title']}: {row['stem']}"
            digest = hashlib.sha256(f"{COMPETITION_CODE}|advanced|{full_stem}".encode("utf-8")).hexdigest()
            existing = db.query(Question).filter(
                (Question.competition_id == competition_id) &
                ((Question.hash_norm == digest) | (Question.stem == full_stem))
            ).first()
            if existing:
                existing.case_id = case.id
                existing.is_verified = True
                existing.quality_report = {"review": "source_grounded", "bank": COMPETITION_CODE}
                continue
            db.add(Question(
                competition_id=competition_id, case_id=case.id, question_id=str(uuid.uuid4()),
                track="FUNCIONAL", competency="Análisis y decisión en gestión de TI",
                topic=f"UApA - {case_data['domain']}", macro_dominio="Casos integrados de arquitectura y gestión TI",
                micro_competencia=case_data["domain"], difficulty=3, question_type="SITUATIONAL",
                stem=full_stem, options_json=row["options"], correct_key=row["correct"],
                rationale=row["rationale"], source_refs=case_data["source"], hash_norm=digest,
                is_verified=True, quality_report={"review": "source_grounded", "bank": COMPETITION_CODE},
            ))
            created += 1
    db.commit()
    return created


def remove_obsolete_advanced_questions(db, competition_id: int) -> int:
    """Retira la cuarta pregunta del prototipo para conservar tripletas tipo GOA."""
    case_titles = [case[0] for case in ADVANCED_CASES]
    case_ids = [row[0] for row in db.query(CaseStudy.id).filter(
        CaseStudy.competition_id == competition_id,
        CaseStudy.title.in_(case_titles),
    ).all()]
    if not case_ids:
        return 0
    deleted = db.query(Question).filter(
        Question.competition_id == competition_id,
        Question.case_id.in_(case_ids),
        Question.stem.contains("¿Cuál es el riesgo principal de aceptar la propuesta inmediata"),
    ).delete(synchronize_session=False)
    db.commit()
    return deleted
