"""Source-grounded initial study bank for DIAN OPEC 242699 (Analista I)."""

from __future__ import annotations

import hashlib
import uuid

from db.models import CaseStudy, Competition, Question


COMPETITION_CODE = "DIAN-2676-OPEC-242699"
COMPETITION_NAME = "DIAN 2676 · OPEC 242699 · Analista I"
OPEC_NUMBER = "242699"
SOURCE_VERSION = "simo-opec-242699-provided-2026-08-09"
FICHA = "Ficha oficial SIMO OPEC 242699 · Manual Específico DIAN TP-DE-2013"


# The prompts only assess the ten functions in the supplied official profile;
# entity-specific rules not present in that source are intentionally avoided.
CASE_SPECS = (
    (1, "Servicios administrativos y bienes DIAN", "La dependencia recibe una solicitud urgente de traslado de bienes y contratación de transporte. No identifica responsable, inventario, ruta de aprobación ni soportes.", "Organizar la solicitud, verificar responsables, inventario, soportes y procedimiento aplicable antes de tramitarla.", "Solicitud radicada, inventario o relación de bienes, responsables, aprobaciones y soportes del servicio.", "Porcentaje de solicitudes de servicios y bienes tramitadas con soportes completos.", "Perder control sobre bienes, responsabilidades y recursos institucionales."),
    (2, "Procedimientos técnicos de la dependencia", "Una sección pide ejecutar una actividad técnica con una instrucción verbal, aunque el procedimiento vigente exige registros y validación previa.", "Consultar el procedimiento vigente, confirmar el responsable técnico y dejar los registros requeridos antes de ejecutar.", "Procedimiento o instructivo vigente, validación del responsable y registro de la actividad realizada.", "Porcentaje de actividades técnicas ejecutadas con el procedimiento y registro aplicables.", "Aplicar criterios inconsistentes y no poder demostrar el cumplimiento técnico."),
    (3, "Gestión presupuestal y financiera", "En un trámite de pago, la obligación fue reportada, pero no están completos los soportes que permiten relacionarla con disponibilidad, registro presupuestal y orden de pago.", "Verificar la secuencia del hecho financiero y completar o devolver los soportes antes de registrar o continuar el trámite.", "Soportes de disponibilidad, registro presupuestal, obligación, reserva cuando aplique y orden de pago.", "Porcentaje de trámites financieros registrados sin devoluciones por soportes incompletos.", "Generar registros financieros inconsistentes o pagos sin trazabilidad suficiente."),
    (4, "Funciones comunes y servicio público", "El superior asigna una actividad común que requiere coordinación con otras áreas y entrega dentro de un plazo. No existe aún responsable visible de consolidar el avance.", "Aclarar alcance, responsables, plazo y entregables; coordinar el apoyo y reportar oportunamente el avance.", "Asignación, cronograma o compromiso, comunicaciones de coordinación y entrega o reporte final.", "Porcentaje de compromisos comunes entregados dentro del plazo acordado.", "Duplicar esfuerzos, incumplir compromisos o dejar actividades sin responsable."),
    (5, "Mercancías y bienes bajo administración DIAN", "Llegan mercancías aprehendidas a una sede y se solicita su entrega inmediata a un tercero. El expediente no contiene decisión de disposición ni evidencia completa de ingreso y custodia.", "Registrar el ingreso, asegurar custodia e inventario y verificar la decisión y autorizaciones de disposición antes de cualquier egreso.", "Acta de ingreso, inventario, registro de custodia, acto o autorización de disposición y constancia de egreso.", "Porcentaje de bienes con trazabilidad completa desde ingreso hasta disposición o egreso.", "Disponer bienes sin autorización o perder la cadena de custodia."),
    (6, "Inventarios e inspección de bienes", "Durante un inventario se detectan bienes sin clasificación y otros con deterioro visible. Se propone incluirlos como aptos sin inspección para cerrar el reporte a tiempo.", "Inspeccionar, clasificar y registrar el estado de cada bien antes de definir su alistamiento o disposición.", "Inventario actualizado, registro de inspección, clasificación, estado y soportes de alistamiento o disposición.", "Porcentaje de bienes inventariados con clasificación y estado verificados.", "Tomar decisiones sobre bienes con información incompleta o estado no comprobado."),
    (7, "Planeación, control y evaluación", "La oficina inicia varias acciones, pero no ha definido metas, responsables, cronograma ni mecanismo de seguimiento.", "Organizar objetivos, actividades, responsables, plazos, evidencias e indicadores para realizar seguimiento periódico.", "Plan de trabajo, matriz de responsables, cronograma, indicadores y reportes de seguimiento.", "Porcentaje de acciones del plan con avance y evidencia reportados oportunamente.", "No poder controlar avances, detectar retrasos ni evaluar resultados."),
    (8, "Información para planes, programas y proyectos", "Para un informe de proyecto, varias áreas entregan cifras con fechas y definiciones diferentes. Se pide consolidarlas de inmediato sin validación.", "Definir el corte, validar fuentes, consistencia y responsables antes de consolidar la información.", "Fuentes identificadas, fecha de corte, reglas de validación, consolidado y responsables que confirman los datos.", "Porcentaje de reportes entregados con fuente, corte y validación documentados.", "Presentar información inconsistente y afectar decisiones del plan o proyecto."),
    (9, "Actos administrativos y documentos", "Se solicita proyectar un acto administrativo con urgencia, pero solo hay una instrucción general sin antecedentes, competencia, hechos ni soportes técnicos.", "Solicitar y organizar antecedentes, hechos, competencia, soportes y revisión requerida antes de proyectar el documento.", "Solicitud, antecedentes, soportes técnicos, borrador trazable y constancia de revisión por el responsable competente.", "Porcentaje de documentos proyectados con antecedentes y soportes completos.", "Producir documentos sin fundamento suficiente o con errores de alcance."),
    (10, "Soporte de plataformas y servicios de información", "Un usuario informa que una plataforma institucional no permite completar un trámite. Se propone cambiar la configuración sin registrar el incidente ni evaluar el impacto.", "Registrar el incidente, recoger evidencia, clasificarlo, escalarlo según el soporte técnico y verificar la solución antes de cerrar.", "Ticket o registro de soporte, evidencia del error, responsable asignado, acciones realizadas y prueba de cierre.", "Porcentaje de incidentes resueltos dentro del tiempo acordado y con cierre verificado.", "Afectar otros servicios, perder trazabilidad y repetir fallas sin diagnóstico."),
)


def _options(correct: str, wrong_one: str, wrong_two: str, offset: int) -> tuple[dict[str, str], str]:
    values = [correct, wrong_one, wrong_two]
    values = values[offset % 3:] + values[:offset % 3]
    options = dict(zip(("A", "B", "C"), values))
    return options, next(key for key, value in options.items() if value == correct)


def _source(function: int) -> str:
    return f"{FICHA} · función {function}"


def case_questions(spec: tuple, case_index: int) -> list[dict]:
    number, topic, _, action, evidence, _, risk = spec
    prompts = (
        ("¿Cuál es la actuación inicial más adecuada?", action, "Ejecutar la solicitud de inmediato y reunir los soportes al final.", "Trasladar toda la decisión a quien hizo la solicitud sin validar el procedimiento."),
        ("¿Qué evidencia debe quedar disponible para sustentar la actuación?", evidence, "Un mensaje informal sin responsable, fecha ni anexos.", "Solo una manifestación verbal de que la actividad fue realizada."),
        ("¿Cuál es el riesgo principal de omitir los controles descritos?", risk, "Que el trámite se vuelva automáticamente prioritario.", "Que la dependencia tenga más reuniones de seguimiento."),
    )
    return [
        {"stem": prompt, "options": options, "correct_key": key,
         "rationale": f"La ficha asigna al Analista I apoyo técnico, administrativo y operativo con trazabilidad. {correct}"}
        for index, (prompt, correct, wrong_one, wrong_two) in enumerate(prompts)
        for options, key in [_options(correct, wrong_one, wrong_two, case_index + index)]
    ]


def standalone_questions(spec: tuple, case_index: int) -> list[dict]:
    _, topic, _, action, evidence, indicator, risk = spec
    prompts = (
        (f"En {topic.lower()}, ¿qué debe hacerse antes de continuar un trámite incompleto?", action, "Continuar para cumplir el plazo y corregir después.", "Omitir los soportes para evitar retrasos."),
        (f"¿Qué elemento permite comprobar la trazabilidad en {topic.lower()}?", evidence, "Una conversación sin radicación ni anexos.", "La memoria de quien atendió la actividad."),
        (f"¿Qué indicador es más pertinente para hacer seguimiento a {topic.lower()}?", indicator, "Número de correos enviados por el equipo.", "Cantidad de reuniones sin resultado documentado."),
        (f"¿Qué consecuencia debe prevenirse al apoyar {topic.lower()}?", risk, "Que aumente el número de asistentes a una reunión.", "Que el trámite tenga un título más corto."),
        (f"Un tercero pide resolver una situación de {topic.lower()} sin dejar registro. ¿Cuál es la respuesta correcta?", "Aplicar el procedimiento, conservar los soportes y comunicar el estado por los canales definidos.", "Atenderla de forma informal porque la solicitud es urgente.", "Eliminar los registros para evitar consultas posteriores."),
        (f"¿Qué rol corresponde al Analista I frente a {topic.lower()}?", "Preparar y apoyar técnicamente la actuación dentro de los lineamientos, sin sustituir la decisión del responsable competente.", "Aprobar por sí mismo cualquier decisión que llegue a la dependencia.", "Desentenderse de la trazabilidad porque el resultado depende de otra área."),
        (f"Antes de reportar como concluida una actividad de {topic.lower()}, ¿qué debe comprobarse?", "Que el resultado, los soportes y el registro de cierre estén completos y sean verificables.", "Que se haya informado verbalmente a una persona interesada.", "Que haya transcurrido el plazo inicialmente estimado."),
    )
    return [
        {"stem": stem, "options": options, "correct_key": key,
         "rationale": f"La respuesta se deriva del alcance funcional de la OPEC 242699: {correct}"}
        for index, (stem, correct, wrong_one, wrong_two) in enumerate(prompts)
        for options, key in [_options(correct, wrong_one, wrong_two, case_index + index + 1)]
    ]


def _competition(db) -> Competition:
    competition = db.query(Competition).filter_by(code=COMPETITION_CODE).first()
    if competition is None:
        competition = Competition(code=COMPETITION_CODE, name=COMPETITION_NAME, entity="DIAN", is_active=True)
        db.add(competition)
        db.flush()
    return competition


def seed_bank(db) -> tuple[int, int]:
    """Load 10 complete GOA cases plus 70 individual questions, idempotently."""
    competition = _competition(db)
    cases_added = questions_added = 0
    for case_index, spec in enumerate(CASE_SPECS, start=1):
        function, topic, text, *_ = spec
        case_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{COMPETITION_CODE}:case:{function}"))
        if db.get(CaseStudy, case_id) is None:
            db.add(CaseStudy(id=case_id, competition_id=competition.id, title=f"OPEC {OPEC_NUMBER} F{function} · {topic}", text=text, topic=topic, difficulty=2))
            cases_added += 1
        for kind, rows in (("case", case_questions(spec, case_index)), ("single", standalone_questions(spec, case_index))):
            for row in rows:
                stem = f"Caso F{function}: {row['stem']}" if kind == "case" else row["stem"]
                digest = hashlib.sha256(f"{COMPETITION_CODE}|{stem}".encode("utf-8")).hexdigest()
                question = db.query(Question).filter_by(competition_id=competition.id, hash_norm=digest).first()
                if question is None:
                    question = Question(question_id=str(uuid.uuid4()), hash_norm=digest)
                    db.add(question)
                    questions_added += 1
                question.competition_id = competition.id
                question.case_id = case_id if kind == "case" else None
                question.track = "FUNCIONAL"
                question.competency = topic
                question.topic = topic
                question.macro_dominio = "Gestión operativa y administrativa DIAN"
                question.micro_competencia = f"OPEC {OPEC_NUMBER} F{function}"
                question.difficulty = 2 if kind == "case" else 1 + ((case_index + len(stem)) % 3)
                question.question_type = "SITUATIONAL"
                question.stem = stem
                question.options_json = row["options"]
                question.correct_key = row["correct_key"]
                question.rationale = row["rationale"]
                question.source_refs = _source(function)
                question.is_verified = True
                question.quality_report = {"status": "APPROVED", "review": "source_grounded_editorial", "source_version": SOURCE_VERSION, "opec": OPEC_NUMBER}
    db.commit()
    return cases_added, questions_added
