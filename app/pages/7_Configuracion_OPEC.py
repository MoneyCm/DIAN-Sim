import streamlit as st
import os, sys, json, re

# --- ESCUDO DE RUTAS MIKEY v25 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Competition, Question, UserOPEC
from ui_utils import load_css, render_header

from core.auth import AuthManager
from core.competitions import ensure_builtin_competitions
from core.competition_catalog import is_hidden_catalog_duplicate, load_catalog_profiles
from core.competition_detection import competition_matches, detect_competition_from_simo
from core.opec_profiles import unique_opec_profiles
from core.question_banks.alimentacion_escolar import (
    TARGET_COUNT as ALIMENTACION_ESCOLAR_TARGET,
    seed_advanced_cases as seed_alimentacion_escolar_advanced_cases,
    seed_questions as seed_alimentacion_escolar_questions,
)

# pass # Removed st.set_page_config

def extract_opec_profile_from_text(text):
    """Extrae los campos relevantes de una ficha copiada desde SIMO."""
    if len(text.strip()) < 40:
        raise ValueError("Pega el texto completo de la ficha de empleo de SIMO.")

    def field(pattern):
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""

    def section(start, end):
        match = re.search(rf"{start}\s*[:\-]?\s*(.*?)(?=\s*{end}\b|\Z)", text, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    functions_raw = section(r"Funciones", r"Requisitos|Equivalencias|Vacantes")
    matches = re.findall(r"(?:^|\n)\s*\d{1,2}\s*[\.)]\s*(.*?)(?=(?:\n\s*\d{1,2}\s*[\.)])|\Z)", functions_raw, flags=re.DOTALL)
    functions = [re.sub(r"\s+", " ", value).strip() for value in matches if value.strip()]
    if not functions and functions_raw:
        functions = [re.sub(r"\s+", " ", functions_raw).strip()]

    denomination = field(r"(?:Denominaci[oó]n|Nombre\s+del\s+Cargo)\s*:?[ \t]*(.*?)(?=\s+(?:Grado|C[oó]digo)\s*:|\n)")
    grade = field(r"Grado\s*:?[ \t]*(\d+)")
    opec_number = field(r"(?:N[uú]mero\s+)?OPEC\s*[:#]?\s*(\d{4,})")
    job_title = " ".join(part for part in [denomination, f"Grado {grade}" if grade else ""] if part)
    return {
        "opec_number": opec_number,
        "job_title": job_title or (f"Empleo OPEC {opec_number}" if opec_number else ""),
        "level": field(r"Nivel\s*:?[ \t]*(.*?)(?=\s+(?:Denominaci[oó]n|Nombre\s+del\s+Cargo)\s*:|\n)"),
        "purpose": re.sub(r"\s+", " ", section(r"Prop[oó]sito", r"Funciones|Requisitos|Equivalencias")).strip(),
        "functions": functions,
        "requirements": re.sub(r"\s+", " ", section(r"Requisitos", r"Equivalencias|Vacantes")).strip(),
        "competition": detect_competition_from_simo(text),
    }


TERRITORIAL_12_SEED = [
    ("¿Cuál es la finalidad de las pruebas del proceso de selección?", {"A": "Apreciar capacidad, idoneidad, adecuación y potencialidad para el empleo.", "B": "Reemplazar la verificación de requisitos mínimos.", "C": "Asignar automáticamente una vacante por antigüedad."}, "A", "Las pruebas buscan valorar las calidades y competencias requeridas para desempeñar eficazmente el empleo."),
    ("Para la OPEC 241130, ¿qué instrumento debe guardar coherencia con las metas proyectadas y la distribución de recursos?", {"A": "El POAI y los planes de acción por área.", "B": "El registro civil de los aspirantes.", "C": "El listado de inscritos del concurso."}, "A", "La función del empleo ordena elaborar el plan indicativo, planes de acción y POAI en concordancia con metas y recursos."),
    ("¿Qué debe verificarse antes de aprobar el plan de inversiones del Plan de Desarrollo Educativo?", {"A": "Su coherencia con el componente estratégico y los programas y proyectos prioritarios.", "B": "Que todos los proyectos tengan el mismo presupuesto.", "C": "Que no existan indicadores."}, "A", "La ficha de la OPEC exige verificar coherencia estratégica e inclusión de prioridades."),
    ("¿Cuál conjunto de indicadores corresponde al seguimiento de metas previsto para el cargo?", {"A": "Impacto, eficiencia y eficacia.", "B": "Color, antigüedad y ubicación.", "C": "Únicamente número de reuniones."}, "A", "La función 7 señala expresamente indicadores de impacto, eficiencia y eficacia."),
    ("¿Qué finalidad tiene semaforizar las metas por plan, programa y proyecto?", {"A": "Revalidar acciones orientadas al cumplimiento.", "B": "Sustituir el plan de desarrollo.", "C": "Eliminar la rendición de cuentas."}, "A", "La función 9 relaciona la semaforización con acciones para el cumplimiento."),
    ("La formulación de planes, programas y proyectos requiere levantar información conforme a:", {"A": "Las metodologías establecidas.", "B": "Preferencias personales del equipo.", "C": "Información no verificable."}, "A", "La función 6 exige aplicar las metodologías establecidas."),
    ("¿Qué condición debe cumplir una persona inscrita en modalidad Abierto para continuar en el proceso?", {"A": "Acreditar requisitos de participación y requisitos mínimos del empleo.", "B": "Tener experiencia únicamente en el sector privado.", "C": "Haber presentado una prueba de integridad independiente."}, "A", "El Acuerdo y Anexo regulan requisitos de participación y verificación de requisitos mínimos."),
    ("¿Cuál afirmación sobre la verificación de requisitos mínimos es correcta?", {"A": "Es una condición obligatoria y no una prueba de selección.", "B": "Reemplaza las pruebas escritas.", "C": "Solo aplica luego de la lista de elegibles."}, "A", "La normativa CNSC distingue la verificación de requisitos mínimos de las pruebas de selección."),
    ("Al elaborar el plan indicativo, el servidor debe articularlo principalmente con:", {"A": "Metas proyectadas y distribución de recursos.", "B": "Preferencias individuales.", "C": "Actividades sin indicador."}, "A", "La función 5 exige esa concordancia."),
    ("Si un indicador muestra atraso crítico en una meta, la acción adecuada es:", {"A": "Analizar causas y revalidar acciones de cumplimiento.", "B": "Eliminar la meta del reporte.", "C": "Cambiar el indicador sin justificación."}, "A", "La semaforización sirve para orientar acciones de cumplimiento."),
    ("¿Qué distingue un indicador de eficiencia?", {"A": "Relaciona resultados con recursos utilizados.", "B": "Solo describe una actividad realizada.", "C": "Mide exclusivamente percepción."}, "A", "La eficiencia evalúa la relación entre recursos y productos o resultados."),
    ("¿Qué debe hacer el cargo antes de gestionar la aprobación del POAI?", {"A": "Verificar la necesidad de coordinar ajustes cuando sean necesarios.", "B": "Eliminar los proyectos prioritarios.", "C": "Aprobarlo sin revisar metas."}, "A", "La función 8 prevé gestión de aprobación y coordinación de ajustes."),
    ("La coordinación de un grupo temporal debe realizarse conforme a:", {"A": "Los lineamientos del superior inmediato.", "B": "Decisiones informales de terceros.", "C": "El criterio exclusivo de cada integrante."}, "A", "La función 2 fija ese lineamiento."),
    ("La coordinación de grupos permanentes se ejerce de acuerdo con:", {"A": "El respectivo acto administrativo del Gobernador.", "B": "Una instrucción verbal sin soporte.", "C": "La decisión de un contratista."}, "A", "La función 1 exige el acto administrativo correspondiente."),
    ("Para revisar componentes estratégicos del sector, el criterio rector es:", {"A": "Los lineamientos normativos aplicables.", "B": "La improvisación presupuestal.", "C": "La eliminación de evidencias."}, "A", "La función 3 exige ceñirse a los lineamientos normativos."),
    ("¿Qué evidencia respalda mejor el seguimiento a metas de un proyecto?", {"A": "Indicadores definidos, línea base, meta y resultado periódico.", "B": "Una opinión sin datos.", "C": "Solo el nombre del proyecto."}, "A", "El seguimiento exige información verificable para medir resultados."),
]

TERRITORIAL_12_SECOND_SEED = [
    ("Para un empleo profesional ordinario de Territorial 12, ¿qué peso tiene la prueba de competencias funcionales?", {"A": "20%", "B": "60%", "C": "30%"}, "B", "La Tabla 6 del Acuerdo 36 asigna 60% a competencias funcionales.", "Acuerdo 36 de 2025, artículo 16, tabla 6"),
    ("¿Cuál es el puntaje mínimo aprobatorio de la prueba funcional?", {"A": "65,00", "B": "70,00", "C": "No tiene mínimo"}, "A", "La prueba funcional es eliminatoria y exige 65,00 puntos.", "Acuerdo 36 de 2025, artículo 16, tabla 6"),
    ("¿Qué carácter tiene la prueba de competencias comportamentales?", {"A": "Eliminatorio", "B": "Habilitante", "C": "Clasificatorio"}, "C", "El Acuerdo la define como clasificatoria.", "Acuerdo 36 de 2025, artículo 16, tabla 6"),
    ("¿Qué peso tiene la prueba de competencias comportamentales para la OPEC 241130?", {"A": "20%", "B": "40%", "C": "60%"}, "A", "Para empleos ordinarios, la Tabla 6 le asigna 20%.", "Acuerdo 36 de 2025, artículo 16, tabla 6"),
    ("¿Qué peso tiene la valoración de antecedentes para este empleo profesional?", {"A": "10%", "B": "20%", "C": "No se aplica"}, "B", "La Tabla 6 asigna 20% a la valoración de antecedentes.", "Acuerdo 36 de 2025, artículo 16, tabla 6"),
    ("Un aspirante obtiene 64,99 en competencias funcionales. ¿Qué ocurre?", {"A": "Continúa por haber presentado la prueba", "B": "Solo pierde la valoración de antecedentes", "C": "No continúa porque no alcanzó el mínimo eliminatorio"}, "C", "Quien no obtiene 65,00 en la funcional queda excluido.", "Anexo Técnico Territorial 12, numeral 4"),
    ("¿A quiénes se publican los resultados de las pruebas clasificatorias?", {"A": "Solo a quienes superaron la prueba eliminatoria", "B": "A todos los inscritos", "C": "Únicamente a quienes reclamaron"}, "A", "El Anexo condiciona su publicación a superar la prueba eliminatoria.", "Anexo Técnico Territorial 12, numeral 4"),
    ("¿Qué mide principalmente la prueba funcional?", {"A": "La antigüedad del aspirante", "B": "La aplicación de conocimientos, capacidades y habilidades en contexto laboral", "C": "Solo rasgos de personalidad"}, "B", "La definición se centra en aplicar conocimientos y capacidades al empleo específico.", "Anexo Técnico Territorial 12, numeral 4, literal a"),
    ("¿Qué evalúa la prueba comportamental?", {"A": "Capacidades, habilidades, rasgos y actitudes que potencian el desempeño", "B": "Únicamente conocimientos jurídicos", "C": "La documentación aportada en SIMO"}, "A", "El literal b del numeral 4 define ese objeto.", "Anexo Técnico Territorial 12, numeral 4, literal b"),
    ("¿Cómo se califican las pruebas funcional y comportamental?", {"A": "En escala de 1 a 5", "B": "Solo como aprobado o no aprobado", "C": "De 0 a 100, con parte entera y dos decimales truncados"}, "C", "El Anexo fija una escala de cero a cien y dos decimales truncados.", "Anexo Técnico Territorial 12, numeral 4"),
    ("¿Con cuánta anticipación mínima debe informarse la citación a pruebas?", {"A": "Dos días calendario", "B": "Cinco días hábiles", "C": "Quince días hábiles"}, "B", "La citación debe informarse por lo menos con cinco días hábiles de anticipación.", "Anexo Técnico Territorial 12, numeral 4"),
    ("¿Dónde consulta el aspirante la citación oficial?", {"A": "En el sitio de la CNSC, enlace SIMO", "B": "En redes sociales no oficiales", "C": "En la alcaldía del municipio"}, "A", "La CNSC comunica la citación mediante su sitio web y SIMO.", "Anexo Técnico Territorial 12, numeral 4"),
    ("¿Las pruebas funcional y comportamental se aplican en fechas distintas?", {"A": "Sí, siempre con una semana de diferencia", "B": "Depende del puntaje previo", "C": "No; se aplican en la misma fecha y hora"}, "C", "El Anexo dispone aplicación en la misma fecha y hora.", "Anexo Técnico Territorial 12, numeral 4"),
    ("Para la OPEC ubicada en Turbaco, ¿es Turbaco una ciudad prevista para pruebas escritas?", {"A": "No, solo Bogotá", "B": "Sí", "C": "Solo para pruebas de conducción"}, "B", "Turbaco figura entre las ciudades de aplicación de pruebas escritas.", "Anexo Técnico Territorial 12, numeral 4.2"),
    ("¿Cuál es el plazo para reclamar contra los resultados de pruebas escritas?", {"A": "Cinco días hábiles siguientes a la publicación", "B": "Dos meses", "C": "Un día calendario"}, "A", "El numeral 4.4 establece cinco días hábiles.", "Anexo Técnico Territorial 12, numeral 4.4"),
    ("¿Por qué medio se presenta una reclamación contra resultados?", {"A": "Correo personal del evaluador", "B": "Ventanilla física de la Gobernación", "C": "Únicamente mediante SIMO"}, "C", "El Anexo exige presentar la reclamación por SIMO.", "Anexo Técnico Territorial 12, numeral 4.4"),
    ("¿Puede un aspirante reclamar sobre los resultados de otra persona?", {"A": "Sí, si conoce su número de documento", "B": "No; solo puede reclamar frente a sus propios resultados", "C": "Sí, con autorización verbal"}, "B", "El derecho de reclamación se limita a los resultados propios.", "Anexo Técnico Territorial 12, numeral 4.4"),
    ("Durante una reclamación de VRM, ¿pueden agregarse documentos nuevos?", {"A": "No; se consideran extemporáneos", "B": "Sí, sin límite", "C": "Solo después de la lista de elegibles"}, "A", "La reclamación no permite complementar o reemplazar documentos aportados antes del cierre.", "Anexo Técnico Territorial 12, numeral 3.5"),
    ("¿Qué elementos están prohibidos en el sitio de aplicación?", {"A": "Únicamente alimentos", "B": "Solo documentos impresos", "C": "Material de consulta y dispositivos electrónicos, entre otros elementos señalados"}, "C", "El Anexo prohíbe documentos de consulta y dispositivos electrónicos o de grabación.", "Anexo Técnico Territorial 12, numeral 4, nota 1"),
    ("Si se usa cédula digital, ¿qué regla aplica al teléfono?", {"A": "Puede usarse durante toda la prueba", "B": "Puede ingresar excepcionalmente, pero debe permanecer apagado y ubicarse donde indiquen", "C": "Puede utilizarse como calculadora"}, "B", "La excepción es solo para identificación y exige mantenerlo apagado.", "Anexo Técnico Territorial 12, numeral 4, nota 1"),
]

# Cada escenario produce cuatro preguntas situacionales: decisión, evidencia,
# indicador y riesgo. Junto con los dos bloques anteriores completa 100 ítems.
TERRITORIAL_12_SCENARIOS = [
    {
        "domain": "Alineación con el PDD",
        "situation": "Una dependencia propone un proyecto educativo atractivo, pero no demuestra relación con ninguna meta del Plan Departamental de Desarrollo.",
        "action": "Solicitar la trazabilidad entre problema, objetivo, producto, meta e indicador del PDD antes de priorizarlo.",
        "evidence": "Matriz de articulación que vincule el proyecto con metas, indicadores y recursos del PDD.",
        "indicator": "Porcentaje de productos del proyecto que contribuyen a metas verificables del PDD.",
        "risk": "Asignar recursos a actividades sin contribución demostrable a los resultados departamentales.",
        "source": "Ficha OPEC 241130, propósito y funciones 3, 4 y 5",
    },
    {
        "domain": "Plan Operativo Anual de Inversiones",
        "situation": "El techo presupuestal disminuye y el POAI contiene proyectos cuyo costo supera los recursos disponibles.",
        "action": "Revisar prioridades, metas, fuentes y cronogramas, documentar los ajustes y tramitar nuevamente la aprobación.",
        "evidence": "Versión ajustada del POAI con trazabilidad de cambios, concepto técnico y disponibilidad de recursos.",
        "indicator": "Porcentaje del valor del POAI respaldado por fuentes de financiación identificadas.",
        "risk": "Aprobar compromisos sin respaldo financiero o sacrificar metas prioritarias sin justificación.",
        "source": "Ficha OPEC 241130, funciones 5 y 8",
    },
    {
        "domain": "Plan indicativo",
        "situation": "El plan indicativo registra metas cuatrienales, pero no distribuye los resultados esperados por vigencia.",
        "action": "Desagregar las metas por anualidad y relacionarlas con responsables, productos e indicadores.",
        "evidence": "Plan indicativo aprobado con programación anual, líneas base, metas y responsables.",
        "indicator": "Porcentaje de metas cuatrienales con programación anual completa.",
        "risk": "Impedir el seguimiento oportuno y detectar los retrasos solo al finalizar el periodo de gobierno.",
        "source": "Ficha OPEC 241130, función 5",
    },
    {
        "domain": "Planes de acción",
        "situation": "Un área reporta numerosas actividades, pero ninguna señala responsable, plazo o producto verificable.",
        "action": "Reformular el plan de acción con actividades, productos, responsables, plazos, recursos e indicadores.",
        "evidence": "Plan de acción firmado y matriz de seguimiento con soportes de avance.",
        "indicator": "Porcentaje de actividades del plan cumplidas oportunamente y con evidencia válida.",
        "risk": "Confundir ejecución de tareas con cumplimiento efectivo de metas institucionales.",
        "source": "Ficha OPEC 241130, funciones 5 y 7",
    },
    {
        "domain": "Plan de Desarrollo Educativo",
        "situation": "El plan de inversiones educativo incluye iniciativas dispersas que no corresponden a los programas prioritarios definidos.",
        "action": "Contrastar cada iniciativa con el componente estratégico y devolver para ajuste las que carezcan de coherencia.",
        "evidence": "Concepto técnico de coherencia entre diagnóstico, programas prioritarios, metas e inversiones.",
        "indicator": "Proporción de inversión educativa destinada a programas y proyectos priorizados.",
        "risk": "Fragmentar recursos y reducir el efecto de la inversión sobre los problemas educativos identificados.",
        "source": "Ficha OPEC 241130, función 4",
    },
    {
        "domain": "Levantamiento de información",
        "situation": "Dos equipos presentan cifras diferentes sobre cobertura educativa y no documentan su origen ni fecha de corte.",
        "action": "Definir una metodología común, validar las fuentes y documentar responsables, fecha de corte y reglas de calidad.",
        "evidence": "Ficha técnica del dato, base validada y registro de controles de consistencia.",
        "indicator": "Porcentaje de registros que superan los controles de completitud, consistencia y oportunidad.",
        "risk": "Formular proyectos y metas con diagnósticos contradictorios o no reproducibles.",
        "source": "Ficha OPEC 241130, función 6",
    },
    {
        "domain": "Seguimiento de metas",
        "situation": "Una meta presenta avance físico del 40% cuando, según la programación, debería alcanzar el 70%.",
        "action": "Analizar la desviación, identificar causas, acordar acciones correctivas y actualizar el seguimiento.",
        "evidence": "Informe de desviaciones con causas, responsables, compromisos y fechas de recuperación.",
        "indicator": "Brecha porcentual entre avance físico ejecutado y avance físico programado.",
        "risk": "Mantener la misma ejecución y cerrar la vigencia con incumplimiento de la meta.",
        "source": "Ficha OPEC 241130, funciones 7 y 9",
    },
    {
        "domain": "Eficiencia",
        "situation": "Dos proyectos entregan el mismo producto, pero uno utiliza el doble de recursos y tiempo.",
        "action": "Comparar procesos y costos unitarios para identificar causas y oportunidades de optimización.",
        "evidence": "Análisis de costos, tiempos, productos y factores que explican la diferencia.",
        "indicator": "Costo promedio por producto educativo entregado.",
        "risk": "Mantener ineficiencias que reducen la cantidad de beneficiarios atendidos con los recursos disponibles.",
        "source": "Ficha OPEC 241130, función 7",
    },
    {
        "domain": "Eficacia",
        "situation": "Un programa ejecutó todo su presupuesto, pero alcanzó solamente la mitad de la meta de beneficiarios.",
        "action": "Evaluar el cumplimiento del resultado, explicar la desviación y definir medidas de recuperación.",
        "evidence": "Comparación documentada entre meta programada, resultado alcanzado y población efectivamente atendida.",
        "indicator": "Porcentaje de cumplimiento de la meta de beneficiarios.",
        "risk": "Presentar la ejecución presupuestal como éxito aunque el resultado institucional no se haya logrado.",
        "source": "Ficha OPEC 241130, función 7",
    },
    {
        "domain": "Impacto",
        "situation": "Un proyecto entregó dotaciones a todas las sedes previstas, pero no se sabe si mejoró la calidad educativa.",
        "action": "Complementar el indicador de producto con mediciones de resultado o impacto relacionadas con el problema intervenido.",
        "evidence": "Línea base y medición posterior comparable de la variable de resultado seleccionada.",
        "indicator": "Variación de la brecha de aprendizaje o del resultado educativo atribuible a la intervención.",
        "risk": "Concluir que hubo transformación únicamente porque se entregaron bienes o servicios.",
        "source": "Ficha OPEC 241130, función 7",
    },
    {
        "domain": "Semaforización",
        "situation": "El tablero marca una meta en verde porque se ejecutó el presupuesto, aunque el avance físico está retrasado.",
        "action": "Definir reglas de semaforización que integren avance físico, financiero, plazo y calidad de la evidencia.",
        "evidence": "Ficha del indicador con umbrales, fórmula, periodicidad y fuentes de verificación.",
        "indicator": "Número de metas en alerta cuya clasificación fue sustentada con información física y financiera.",
        "risk": "Ocultar retrasos reales mediante una lectura aislada de la ejecución presupuestal.",
        "source": "Ficha OPEC 241130, función 9",
    },
    {
        "domain": "Coordinación de grupo permanente",
        "situation": "Se solicita coordinar de manera permanente un equipo, pero no se identifica el acto administrativo que lo conforma.",
        "action": "Verificar el acto administrativo, su alcance, integrantes y responsabilidades antes de ejercer la coordinación.",
        "evidence": "Acto administrativo vigente y plan de trabajo alineado con las responsabilidades asignadas.",
        "indicator": "Porcentaje de compromisos del grupo permanente cumplidos dentro del plazo acordado.",
        "risk": "Asumir funciones o impartir instrucciones sin competencia o alcance claramente definido.",
        "source": "Ficha OPEC 241130, función 1",
    },
    {
        "domain": "Coordinación de grupo temporal",
        "situation": "Un equipo temporal recibe tareas contradictorias de varias dependencias y empieza a duplicar esfuerzos.",
        "action": "Aclarar objetivo, alcance, responsables y canal de decisión conforme a los lineamientos del superior inmediato.",
        "evidence": "Plan de trabajo temporal con entregables, responsables, cronograma y reglas de coordinación.",
        "indicator": "Porcentaje de entregables temporales aceptados en la fecha prevista.",
        "risk": "Duplicar actividades, incumplir plazos y producir resultados incompatibles.",
        "source": "Ficha OPEC 241130, función 2",
    },
    {
        "domain": "Revisión normativa",
        "situation": "Un componente estratégico propone una solución rápida, pero no identifica las normas que regulan la competencia departamental.",
        "action": "Verificar competencia, marco normativo y restricciones antes de emitir concepto favorable.",
        "evidence": "Matriz normativa vigente con análisis de aplicabilidad y concepto técnico-jurídico.",
        "indicator": "Porcentaje de componentes estratégicos revisados con soporte normativo completo.",
        "risk": "Aprobar acciones inviables, contrarias al marco aplicable o fuera de la competencia institucional.",
        "source": "Ficha OPEC 241130, función 3",
    },
    {
        "domain": "Priorización de proyectos",
        "situation": "Hay recursos para financiar solo dos de cinco proyectos que contribuyen al mismo objetivo sectorial.",
        "action": "Aplicar criterios transparentes de alineación, impacto, viabilidad, población beneficiaria, costo y urgencia.",
        "evidence": "Matriz de priorización con criterios, ponderaciones, puntajes y justificación de la decisión.",
        "indicator": "Porcentaje de recursos asignados a proyectos viables y de mayor puntaje de priorización.",
        "risk": "Seleccionar proyectos por presión informal y no por su contribución demostrable al objetivo público.",
        "source": "Ficha OPEC 241130, funciones 3, 4 y 5",
    },
    {
        "domain": "Gestión de ajustes",
        "situation": "Durante la ejecución cambia una condición crítica y el proyecto requiere modificar cronograma y metas.",
        "action": "Sustentar técnicamente el cambio, evaluar sus efectos y tramitar el ajuste por la instancia competente.",
        "evidence": "Solicitud de ajuste con análisis técnico, presupuestal, cronológico y decisión de aprobación.",
        "indicator": "Porcentaje de ajustes formalizados antes de ejecutar las condiciones modificadas.",
        "risk": "Ejecutar cambios sin autorización, perder trazabilidad y distorsionar la medición de resultados.",
        "source": "Ficha OPEC 241130, función 8",
    },
]


def build_territorial_12_scenario_questions():
    """Construye 64 preguntas situacionales, cuatro por escenario."""
    rows = []
    letters = ("A", "B", "C")

    def options_with_answer(correct_text, distractor_1, distractor_2, offset):
        values = [correct_text, distractor_1, distractor_2]
        rotated = values[offset:] + values[:offset]
        options = dict(zip(letters, rotated))
        correct_key = letters[rotated.index(correct_text)]
        return options, correct_key

    for index, scenario in enumerate(TERRITORIAL_12_SCENARIOS):
        prompts = [
            (
                f"{scenario['situation']} ¿Cuál es la actuación más adecuada del Profesional Especializado?",
                scenario["action"],
                "Archivar el asunto sin análisis ni comunicación a los responsables.",
                "Modificar metas y recursos de manera informal para que el reporte aparezca cumplido.",
                f"La actuación adecuada es {scenario['action'].lower()}",
            ),
            (
                f"En el escenario de {scenario['domain'].lower()}, ¿cuál es el soporte más útil para una decisión verificable?",
                scenario["evidence"],
                "Comentarios verbales sin fecha, responsable ni fuente identificable.",
                "Una presentación sin datos de respaldo ni control de versiones.",
                f"La evidencia pertinente es: {scenario['evidence']}",
            ),
            (
                f"¿Cuál indicador permite seguir mejor el escenario de {scenario['domain'].lower()}?",
                scenario["indicator"],
                "Cantidad de correos enviados por el equipo durante el mes.",
                "Número de páginas que contiene el informe de seguimiento.",
                f"El indicador propuesto mide directamente el desempeño relevante: {scenario['indicator']}",
            ),
            (
                f"¿Cuál es el principal riesgo de no corregir la situación descrita en {scenario['domain'].lower()}?",
                scenario["risk"],
                "Que todos los indicadores mejoren automáticamente sin intervención.",
                "Que aumente el presupuesto disponible sin necesidad de aprobación.",
                f"El riesgo sustantivo es {scenario['risk'].lower()}",
            ),
        ]
        for question_index, (stem, correct, distractor_1, distractor_2, rationale) in enumerate(prompts):
            options, correct_key = options_with_answer(
                correct, distractor_1, distractor_2, (index + question_index) % 3
            )
            rows.append((stem, options, correct_key, rationale, scenario["source"]))
    return rows


def seed_territorial_12_questions(db, competition_id):
    from db.models import Question
    import uuid
    created = 0
    seed_rows = [(stem, options, correct, rationale, "Ficha OPEC 241130 y Acuerdo 36") for stem, options, correct, rationale in TERRITORIAL_12_SEED]
    seed_rows.extend(TERRITORIAL_12_SECOND_SEED)
    seed_rows.extend(build_territorial_12_scenario_questions())
    for stem, options, correct, rationale, source_ref in seed_rows:
        if db.query(Question).filter(Question.competition_id == competition_id, Question.stem == stem).first():
            continue
        db.add(Question(competition_id=competition_id, question_id=str(uuid.uuid4()), stem=stem, options_json=options, correct_key=correct, rationale=rationale, track="FUNCIONAL", competency="Planeación y gestión pública", topic="Territorial 12 - Bolívar", macro_dominio="Planeación territorial", micro_competencia="Planeación, seguimiento y evaluación", difficulty=2, source_refs=source_ref, hash_norm=str(uuid.uuid4())))
        created += 1
    db.commit()
    return created


def load_saved_opec_profile():
    profile_path = os.path.join(
        PROJECT_ROOT, "data", "concursos", "territorial_12_bolivar_opec_241130", "perfil_concurso.json"
    )
    try:
        with open(profile_path, "r", encoding="utf-8") as source:
            return json.load(source)
    except (OSError, json.JSONDecodeError):
        return None

if not AuthManager.check_auth():
    st.warning("Por favor inicia sesión en la página principal.")
    st.stop()

load_css()
if st.session_state.get("opec_onboarding"):
    st.info("👋 Bienvenido. Completa primero los datos de la ficha del cargo. Después se habilitarán tu dashboard, plan diario y simulacros personalizados.")
render_header(title="Mi Meta: OPEC", subtitle="Configura tu cargo y enfoca tu preparación")

def get_active_opec(competition_id=None):
    db = SessionLocal()
    u_id = st.session_state.get("user_id")
    query = db.query(UserOPEC).filter_by(user_id=u_id)
    if competition_id is not None:
        query = query.filter(UserOPEC.competition_id == competition_id)
    else:
        query = query.filter(UserOPEC.is_active.is_(True))
    opec = query.order_by(UserOPEC.updated_at.desc()).first()
    db.close()
    return opec

u_id = st.session_state.get("user_id")
competition_db = SessionLocal()
ensure_builtin_competitions(competition_db)
catalog_profiles = load_catalog_profiles()
competitions = [
    competition for competition in competition_db.query(Competition).filter_by(is_active=True).order_by(Competition.name).all()
    if not is_hidden_catalog_duplicate(competition, catalog_profiles)
]
current_opec = get_active_opec()

# Inicio guiado: para una persona nueva la ficha SIMO es suficiente. El
# concurso se detecta al confirmar y el registro manual queda como alternativa.
with st.container(border=True):
    st.subheader("👋 ¿Es tu primera vez?")
    st.markdown(
        "**La forma más fácil es pegar la ficha completa del empleo de SIMO.** "
        "La aplicación identifica el concurso, la OPEC, el cargo y sus funciones; "
        "no necesitas llenar cada dato por separado."
    )
    guide_cols = st.columns(3)
    guide_cols[0].markdown("**1. Copia**  \nLa ficha del empleo en SIMO")
    guide_cols[1].markdown("**2. Pega**  \nEl texto en ‘Ficha del empleo’")
    guide_cols[2].markdown("**3. Confirma**  \nY empieza tu preparación")
    st.markdown("#### ¿Solo tienes el número OPEC?")
    lookup_col, lookup_button_col = st.columns([3, 1])
    with lookup_col:
        lookup_number = st.text_input(
            "Número OPEC",
            placeholder="Ej: 252097",
            key="quick_opec_number",
            label_visibility="collapsed",
        )
    with lookup_button_col:
        lookup_requested = st.button(
            "🔎 Buscar ficha", use_container_width=True,
            disabled=not bool(lookup_number.strip()),
        )
    if lookup_requested:
        from core.opec_lookup import find_reusable_opec

        lookup_db = SessionLocal()
        try:
            st.session_state["opec_lookup_result"] = find_reusable_opec(
                lookup_db, lookup_number
            )
        finally:
            lookup_db.close()
        if st.session_state["opec_lookup_result"] is None:
            st.warning(
                "Esta OPEC todavía no está en el catálogo compartido. Consúltala en SIMO "
                "y pega la ficha debajo; después quedará reutilizable por número."
            )
            st.link_button(
                "Abrir búsqueda oficial de SIMO",
                "https://simo.cnsc.gov.co/#ofertaEmpleo",
                use_container_width=True,
            )

    reusable_profile = st.session_state.get("opec_lookup_result")
    if reusable_profile:
        st.success(
            f"Ficha encontrada: OPEC {reusable_profile['opec_number']} · "
            f"{reusable_profile['job_title']}"
        )
        st.caption(
            f"Concurso: {reusable_profile['competition']['name']} · "
            f"{len(reusable_profile['functions'])} funciones registradas. "
            "Revisa la información antes de usarla porque SIMO puede actualizar la oferta."
        )
        with st.expander("Revisar propósito, funciones y requisitos"):
            st.write(reusable_profile["purpose"])
            for index, function in enumerate(reusable_profile["functions"], start=1):
                st.write(f"{index}. {function}")
            st.write(f"**Requisitos:** {reusable_profile['requirements']}")
        if st.button("✅ Usar esta ficha OPEC", type="primary", use_container_width=True):
            from core.opec_lookup import attach_reusable_opec_to_user

            attach_db = SessionLocal()
            try:
                attached = attach_reusable_opec_to_user(
                    attach_db, u_id, reusable_profile
                )
                attach_db.commit()
                target_competition_id = attached.competition_id
                st.session_state.pop("opec_lookup_result", None)
                st.session_state.pop("opec_onboarding", None)
                if target_competition_id:
                    st.session_state["pending_selected_competition_id"] = target_competition_id
                st.success("Ficha asociada y activada para tu cuenta.")
                st.rerun()
            except Exception as exc:
                attach_db.rollback()
                st.error(f"No fue posible asociar la ficha: {exc}")
            finally:
                attach_db.close()
    if st.button("➕ Mi concurso no aparece y quiero registrarlo manualmente", use_container_width=True):
        st.session_state["show_new_competition_form"] = True

competition_ids = [competition.id for competition in competitions]
pending_competition_id = st.session_state.pop("pending_selected_competition_id", None)
if pending_competition_id in competition_ids:
    # This runs before the widget is instantiated, so Streamlit can safely
    # move the selector to a competition just created from a pasted SIMO file.
    st.session_state["selected_competition_id"] = pending_competition_id
default_competition_id = (
    current_opec.competition_id if current_opec and current_opec.competition_id in competition_ids
    else (competition_ids[0] if competition_ids else None)
)
selected_competition_id = st.selectbox(
    "Concurso actual (puedes cambiarlo después)",
    competition_ids,
    index=competition_ids.index(default_competition_id) if default_competition_id in competition_ids else 0,
    format_func=lambda competition_id: next(
        competition.name for competition in competitions if competition.id == competition_id
    ),
    key="selected_competition_id",
) if competition_ids else None
selected_competition = competition_db.get(Competition, selected_competition_id) if selected_competition_id else None
competition_db.close()
active_opec = get_active_opec(selected_competition_id)

if selected_competition and selected_competition.code == "TERRITORIAL-12-BOLIVAR-2685":
    if st.button("Completar banco de 100 preguntas", use_container_width=True):
        seed_db = SessionLocal()
        try:
            created = seed_territorial_12_questions(seed_db, selected_competition_id)
            total = seed_db.query(Question).filter(
                Question.competition_id == selected_competition_id
            ).count()
            st.success(
                f"Se agregaron {created} preguntas. "
                f"Banco actual de Territorial 12: {total} preguntas."
            )
        finally:
            seed_db.close()

    st.caption("Casos GOA revisados para OPEC 241130: 10 situaciones, 3 preguntas por situaci?n.")
    if st.button("Sincronizar casos GOA de OPEC 241130", use_container_width=True):
        from scripts.data.seed_curated_opec241130 import seed as seed_curated_opec241130

        seed_db = SessionLocal()
        try:
            cases, questions = seed_curated_opec241130(apply=True, db=seed_db)
            st.success(
                f"Casos GOA sincronizados: {cases} casos y {questions} preguntas nuevas."
            )
            st.rerun()
        except Exception as exc:
            seed_db.rollback()
            st.error(f"No se pudieron sincronizar los casos GOA: {exc}")
        finally:
            seed_db.close()
if selected_competition and selected_competition.code == "ALIMENTACION-ESCOLAR-ABIERTO":
    seed_db = SessionLocal()
    try:
        current_total = seed_db.query(Question).filter(
            Question.competition_id == selected_competition_id
        ).count()
        current_functional = seed_db.query(Question).filter(
            Question.competition_id == selected_competition_id,
            Question.track == "FUNCIONAL",
        ).count()
        current_behavioral = seed_db.query(Question).filter(
            Question.competition_id == selected_competition_id,
            Question.track == "COMPORTAMENTAL",
        ).count()
    finally:
        seed_db.close()
    st.caption(
        f"Banco del concurso: {current_total} preguntas en total · "
        f"{current_functional} funcionales · {current_behavioral} comportamentales."
    )
    bank_incomplete = current_total < ALIMENTACION_ESCOLAR_TARGET
    if bank_incomplete:
        st.info(
            f"Meta mínima del banco inicial: {ALIMENTACION_ESCOLAR_TARGET} preguntas "
            f"({current_total} disponibles)."
        )
    else:
        st.success(
            f"Meta mínima de {ALIMENTACION_ESCOLAR_TARGET} preguntas alcanzada. "
            "Tener más preguntas aumenta la variedad de los simulacros."
        )
    if bank_incomplete and st.button("Completar banco inicial UApA", use_container_width=True):
        seed_db = SessionLocal()
        try:
            created = seed_alimentacion_escolar_questions(seed_db, selected_competition_id)
            advanced_created = seed_alimentacion_escolar_advanced_cases(seed_db, selected_competition_id)
            total = seed_db.query(Question).filter(
                Question.competition_id == selected_competition_id
            ).count()
            st.success(
                f"Se agregaron {created} preguntas funcionales y {advanced_created} de casos avanzados. "
                f"Banco actual de UApA: {total} preguntas."
            )
        except Exception as exc:
            seed_db.rollback()
            st.error(f"No se pudo completar el banco UApA: {exc}")
        finally:
            seed_db.close()

saved_profile = load_saved_opec_profile()
if (
    saved_profile
    and selected_competition
    and selected_competition.code == saved_profile["competition"]["code"]
    and not active_opec
):
    position = saved_profile["position"]
    st.info(f"Ficha guardada disponible: OPEC {position['opec_number']} — {position['denomination']}.")
    if st.button("Usar ficha guardada para mi cuenta", type="primary", use_container_width=True):
        db = SessionLocal()
        try:
            db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
            saved_values = {
                "competition_id": selected_competition_id,
                "job_title": f"{position['denomination']} Grado {position['grade']}",
                "level": position["level"],
                "purpose": saved_profile.get("purpose"),
                "functions": saved_profile.get("functions", []),
                "requirements": "\n".join([
                    *(f"Estudio: {item}" for item in saved_profile.get("requirements", {}).get("education", [])),
                    f"Experiencia: {saved_profile.get('requirements', {}).get('experience', '')}",
                    f"Otros: {saved_profile.get('requirements', {}).get('other', '')}",
                ]),
                "is_active": True,
            }
            saved_existing = db.query(UserOPEC).filter_by(
                user_id=u_id, opec_number=position["opec_number"]
            ).order_by(UserOPEC.updated_at.desc()).first()
            if saved_existing:
                for field, value in saved_values.items():
                    setattr(saved_existing, field, value)
            else:
                db.add(UserOPEC(
                    user_id=u_id, opec_number=position["opec_number"], **saved_values
                ))
            db.commit()
            st.session_state.pop("opec_onboarding", None)
            st.success("Ficha asociada a tu cuenta de Google.")
            st.rerun()
        except Exception as exc:
            db.rollback()
            st.error(f"No se pudo asociar la ficha: {exc}")
        finally:
            db.close()

if active_opec and not active_opec.is_active:
    if st.button("Usar este concurso y cargo", type="primary", use_container_width=True):
        activate_db = SessionLocal()
        try:
            activate_db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
            selected_opec = activate_db.get(UserOPEC, active_opec.id)
            selected_opec.is_active = True
            activate_db.commit()
            st.success(f"Concurso activo: {selected_competition.name}")
            st.rerun()
        finally:
            activate_db.close()

st.caption(
    "¿Tu concurso no aparece en la lista? Puedes registrarlo sin importar cuál esté seleccionado actualmente."
)
with st.expander(
    "➕ Registrar un concurso nuevo manualmente",
    expanded=st.session_state.get("show_new_competition_form", False),
):
    with st.form("new_competition_form"):
        new_competition_code = st.text_input("Código del proceso", placeholder="Ej: TERRITORIAL-11")
        new_competition_name = st.text_input("Nombre del concurso", placeholder="Ej: Territorial 11")
        new_competition_entity = st.text_input("Entidad", placeholder="Ej: Alcaldía o entidad convocante")
        if st.form_submit_button("Registrar concurso"):
            if not new_competition_code.strip() or not new_competition_name.strip():
                st.error("Indica el código y el nombre del concurso.")
            else:
                create_db = SessionLocal()
                try:
                    code = new_competition_code.strip().upper()
                    existing_competition = create_db.query(Competition).filter_by(code=code).first()
                    if existing_competition:
                        st.warning("Ese concurso ya está registrado.")
                    else:
                        new_competition = Competition(
                            code=code,
                            name=new_competition_name.strip(),
                            entity=new_competition_entity.strip() or None,
                            is_active=True,
                        )
                        create_db.add(new_competition)
                        create_db.flush()
                        new_competition_id = new_competition.id
                        create_db.commit()
                        st.session_state["pending_selected_competition_id"] = new_competition_id
                        st.session_state["show_new_competition_form"] = False
                        st.success("Concurso registrado y seleccionado. Ahora pega la ficha OPEC.")
                        st.rerun()
                finally:
                    create_db.close()

st.markdown("""
<div class="dian-card">
    Configura aquí el <b>Número OPEC</b> de la vacante a la que aspiras. Esto permitirá que la IA genere preguntas 
    específicamente para las funciones y requisitos de tu cargo.
</div>
""", unsafe_allow_html=True)

# Debug session
if st.session_state.get("debug_mode"):
    st.caption(f"🔧 Debug: User ID: {u_id} | Active OPEC: {active_opec.id if active_opec else 'None'}")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Paso recomendado: pega la ficha del empleo")
    st.caption("Copia en SIMO desde los datos del cargo hasta ‘Vacantes’. Detectaremos automáticamente el concurso y la OPEC antes de guardar.")
    employment_text = st.text_area(
        "Ficha de empleo de SIMO",
        placeholder="Pega aquí desde 'Nivel' hasta 'Vacantes'...",
        height=360,
        key="opec_employment_text",
    )

    if employment_text.strip():
        try:
            extracted = extract_opec_profile_from_text(employment_text)
            if not extracted.get("opec_number"):
                st.error("No se pudo identificar el número OPEC. Verifica que hayas pegado la ficha completa de SIMO.")
            else:
                incomplete = [label for label in ("level", "purpose", "functions", "requirements") if not extracted.get(label)]
                if incomplete:
                    st.warning("La ficha se puede guardar, pero el PDF no permitió extraer: " + ", ".join(incomplete) + ".")
                st.success(f"Se identificó la OPEC {extracted['opec_number']}. Revisa la extracción antes de confirmarla.")
                st.markdown(f"**Cargo:** {extracted['job_title']}  ")
                st.markdown(f"**Nivel:** {extracted['level']}  ")
                st.markdown(f"**Funciones detectadas:** {len(extracted['functions'])}")
                detected_competition = extracted.get("competition")
                if detected_competition:
                    st.markdown(f"**Concurso detectado:** {detected_competition['name']}  ")
                    if selected_competition and not competition_matches(
                        detected_competition,
                        selected_name=selected_competition.name,
                        selected_entity=selected_competition.entity or "",
                    ):
                        st.warning(
                            f"La ficha pertenece a {detected_competition['name']}; "
                            f"se guardará en ese concurso y no en {selected_competition.name}."
                        )
                with st.expander("Ver datos extraídos", expanded=False):
                    st.write(extracted["purpose"])
                    st.write(extracted["functions"])
                    st.write(extracted["requirements"])

                if st.button("Confirmar y enfocar simulador", type="primary", use_container_width=True):
                    if selected_competition_id is None:
                        st.error("Primero selecciona o registra un concurso.")
                    else:
                        db = SessionLocal()
                        try:
                            target_competition_id = selected_competition_id
                            detected = extracted.get("competition")
                            if detected and (
                                not selected_competition
                                or not competition_matches(
                                    detected,
                                    selected_name=selected_competition.name,
                                    selected_entity=selected_competition.entity or "",
                                )
                            ):
                                target_competition = db.query(Competition).filter_by(
                                    code=detected["code"]
                                ).first()
                                if target_competition is None:
                                    target_competition = Competition(
                                        code=detected["code"], name=detected["name"],
                                        entity=detected["entity"], is_active=True,
                                        description="Concurso detectado automáticamente desde ficha SIMO.",
                                    )
                                    db.add(target_competition)
                                    db.flush()
                                target_competition_id = target_competition.id

                            db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
                            existing = db.query(UserOPEC).filter_by(
                                user_id=u_id,
                                opec_number=extracted["opec_number"],
                            ).order_by(UserOPEC.updated_at.desc()).first()
                            values = {
                                "competition_id": target_competition_id,
                                "job_title": extracted["job_title"],
                                "level": extracted["level"],
                                "purpose": extracted["purpose"],
                                "functions": extracted["functions"],
                                "requirements": extracted["requirements"],
                                "is_active": True,
                            }
                            if existing:
                                for field, value in values.items():
                                    setattr(existing, field, value)
                            else:
                                db.add(UserOPEC(
                                    user_id=u_id,
                                    competition_id=target_competition_id,
                                    opec_number=extracted["opec_number"],
                                    **values,
                                ))
                            db.commit()
                            st.session_state.pop("opec_onboarding", None)
                            st.session_state["pending_selected_competition_id"] = target_competition_id
                            st.success("Ficha cargada y concurso activado.")
                            st.rerun()
                        except Exception as exc:
                            db.rollback()
                            st.error(f"Error al guardar la ficha: {exc}")
                        finally:
                            db.close()
        except ValueError as exc:
            st.error(str(exc))

with col2:
    st.subheader("🎯 Resumen y Gestión Multi-Cargo")
    
    db_list = SessionLocal()
    stored_user_opecs = db_list.query(UserOPEC).filter_by(user_id=u_id).order_by(UserOPEC.updated_at.desc()).all()
    db_list.close()
    all_user_opecs = unique_opec_profiles(stored_user_opecs)
    
    if all_user_opecs:
        configured_label = "cargo configurado" if len(all_user_opecs) == 1 else "cargos configurados"
        st.write(f"Tienes **{len(all_user_opecs)}** {configured_label}.")
        
        for o in all_user_opecs:
            with st.expander(f"{'⭐' if o.is_active else '📁'} {o.job_title} (OPEC {o.opec_number})", expanded=o.is_active):
                st.write(f"**Nivel:** {o.level}")
                st.write(f"**Propósito:** {o.purpose}")
                
                col_act, col_del = st.columns(2)
                with col_act:
                    if not o.is_active:
                        if st.button("Activar para Estudio", key=f"act_{o.id}"):
                            db = SessionLocal()
                            db.query(UserOPEC).filter_by(user_id=u_id).update({UserOPEC.is_active: False})
                            db.query(UserOPEC).filter_by(id=o.id).update({UserOPEC.is_active: True})
                            db.commit()
                            db.close()
                            st.success(f"Ahora estás enfocado en {o.job_title}")
                            st.rerun()
                with col_del:
                    if st.button("Eliminar Cargo", key=f"del_{o.id}", type="secondary"):
                        db = SessionLocal()
                        db.query(UserOPEC).filter_by(id=o.id).delete()
                        db.commit()
                        db.close()
                        st.rerun()
    else:
        st.warning("No tienes una OPEC configurada todavía. El simulador usará temas generales hasta que definas tu meta.")
        st.image("https://img.icons8.com/color/96/000000/target.png")

st.divider()

if selected_competition_id and active_opec:
    from core.competition_readiness import inspect_competition
    from core.guide_registry import guide_status

    readiness_db = SessionLocal()
    try:
        readiness = inspect_competition(
            readiness_db, selected_competition_id, is_pro=AuthManager.is_pro()
        )
    finally:
        readiness_db.close()
    st.subheader("🧭 Configuración automática del concurso")
    readiness_cols = st.columns(3)
    readiness_cols[0].metric("Preguntas", readiness.question_count)
    readiness_cols[1].metric("Casos verificados", readiness.official_case_count)
    readiness_cols[2].metric(
        "Examen disponible",
        f"{readiness.exam_questions} preguntas" if readiness.exam_questions else "Pendiente",
    )
    st.caption(
        f"Funcionales: {readiness.functional_count} · "
        f"Comportamentales: {readiness.behavioral_count} · "
        f"Duración tipo examen: {readiness.exam_minutes} min"
    )
    st.info(f"Siguiente acción recomendada: {readiness.next_action}")
    thematic_source = guide_status(selected_competition.code)
    if thematic_source["status"] == "pending_official_guide":
        st.warning(
            f"Temario provisional: {thematic_source['label']} · versión {thematic_source['version']}. "
            "Cuando se publique la guía oficial, el banco deberá contrastarse y versionarse de nuevo."
        )
        st.caption(thematic_source["next_action"])

    from core.official_source_research import build_official_source_matrix

    source_matrix = build_official_source_matrix(active_opec, selected_competition)
    monitoring_count = sum(
        row["status"].startswith("monitorear") for row in source_matrix
    )
    with st.expander(
        f"🔎 Investigación oficial provisional · {len(source_matrix)} fuentes",
        expanded=not bool(current_opec),
    ):
        st.write(
            "Esta matriz se construye automáticamente desde las funciones del empleo. "
            "Las fuentes transversales sirven para estudiar desde ahora; las páginas de "
            "CNSC y de la entidad se mantienen en vigilancia hasta que aparezca la guía propia."
        )
        for row in source_matrix:
            status_label = (
                "🟡 Monitorear publicación"
                if row["status"].startswith("monitorear")
                else "🟢 Fuente oficial disponible"
            )
            st.markdown(f"**[{row['title']}]({row['url']})** · {status_label}")
            st.caption(f"{row['area']}: {row['reason']}")
        st.info(
            f"{monitoring_count} fuente(s) requieren seguimiento. "
            "Una guía específica solo se marcará como verificada después de incorporarla y revisarla."
        )

# --- AUTO-SEED SECTION v5.4 ---
st.subheader("🚀 Generación de Base Inicial (Auto-Seed)")
st.markdown("""
Si no quieres crear preguntas una por una, usa esta opción. El sistema leerá tu **Cargo y Funciones** y generará automáticamente:
*   10 casos tipo examen, con 3 preguntas relacionadas por caso.
*   Entre 48 y 60 preguntas funcionales, clasificadas por función y competencia.
*   11 preguntas comportamentales y 11 de integridad/valores.
*   Niveles básico, intermedio y avanzado para la práctica adaptativa.

La base progresiva se crea localmente y no requiere una clave de IA. Al volver a ejecutar
Auto-Seed, el sistema reconoce el banco existente y evita duplicarlo.
""")

if st.button("✨ Generar Base Inicial para este Cargo", type="primary", use_container_width=True):
    if not active_opec:
        st.error("Primero debes guardar la configuración de tu OPEC arriba.")
    else:
        from core.generators.llm import LLMGenerator
        from db.models import CaseStudy, Question
        import uuid
        import time
        
        # Init Generator (Use default provider from settings or fallback to Gemini/Mistral)
        # Note: We need the API Key. For checking purposes we might need to look into settings or ENV.
        # Assuming Global or Env Key is available if configured. 
        # For robustness, we will try to instantiate with explicit checks if possible, 
        # but LLMGenerator handles some defaults.
        
        # Retrieve settings from session or env? 
        # In 4_Generador_IA we get it from UI inputs. Here we assume System Key or User saved key.
        # For now, let's try to instantiate with placeholder and rely on .env if user hasn't set custom.
        
        try:
            from core.config import get_api_key
            mistral_key = get_api_key("mistral")
            gemini_key = get_api_key("gemini")
            api_key = mistral_key or gemini_key
            provider = "mistral" if mistral_key else "gemini"
            # La IA es opcional: el banco progresivo y los casos de respaldo se crean localmente.
            gen = LLMGenerator(provider=provider, api_key=api_key) if api_key else None
            
            progress = st.progress(0, text="Analizando perfil OPEC...")
            status = st.empty()
            
            db = SessionLocal()
            
            total_steps = 4
            current_step = 0
            
            # 1. Generate verified case triplets for the real exam
            from core.exam_format import is_official_functional_payload, official_question_groups
            from core.opec_case_factory import build_fallback_opec_case, build_fallback_questions
            status.info("Generando hasta 10 casos tipo examen...")
            existing_case_rows = db.query(CaseStudy).filter(
                CaseStudy.competition_id == selected_competition_id
            ).all()
            existing_cases = sum(
                1 for case in existing_case_rows if official_question_groups(case)
            )
            for i in range(max(0, 10 - existing_cases)):
                case_number = existing_cases + i + 1
                try:
                    is_adres = getattr(selected_competition, "code", None) == "ADRES-ABIERTO"
                    case_data = build_fallback_opec_case(active_opec, case_number) if is_adres else None
                    source_context = (
                        f"OPEC {active_opec.opec_number}. Propósito: {active_opec.purpose}. "
                        f"Funciones: {active_opec.functions}."
                    )
                    for attempt in range(0 if is_adres or gen is None else 2):
                        try:
                            candidate = gen.generate_case_study(
                                topic=f"Caso {case_number}: {active_opec.job_title}",
                                num_questions=3,
                                difficulty=2,
                                source_context=source_context,
                            )
                        except Exception as generation_exc:
                            print(f"Case {case_number} AI attempt {attempt + 1}: {generation_exc}")
                            candidate = None
                            if "cuota" in str(generation_exc).lower() or "quota" in str(generation_exc).lower():
                                break
                        if is_official_functional_payload(candidate):
                            case_data = candidate
                            break
                        if attempt == 0:
                            status.warning(f"Caso {case_number} con formato incompleto; haciendo un segundo intento...")
                    if case_data is None:
                        case_data = build_fallback_opec_case(active_opec, case_number)
                        status.info(f"Caso {case_number} completado desde la ficha OPEC.")

                    # Save Case
                    new_case = CaseStudy(
                        competition_id=selected_competition_id,
                        id=str(uuid.uuid4()),
                        title=case_data.get("title", "Caso Generado"),
                        text=case_data.get("text"),
                        topic=active_opec.job_title,
                        difficulty=2
                    )
                    db.add(new_case)
                    db.flush()
                    
                    # Save Questions for Case
                    for q in case_data.get("questions", []):
                        micro_comp = q.get('micro_competencia') or q.get('competency') or "General"
                        macro_dom = q.get('macro_dominio') or "Transversal"
                        new_q = Question(
                            competition_id=selected_competition_id,
                            question_id=str(uuid.uuid4()),
                            case_id=new_case.id,
                            stem=q.get("stem"),
                            options_json=q.get("options"),
                            correct_key=q.get("correct_key"),
                            rationale=q.get("rationale"),
                            track=q.get("track", "FUNCIONAL"),
                            competency=micro_comp,
                            micro_competencia=micro_comp,
                            macro_dominio=macro_dom,
                            topic=active_opec.job_title,
                            difficulty=2,
                            question_type="SITUATIONAL",
                            source_refs=f"Ficha OPEC {active_opec.opec_number}",
                            is_verified=True,
                            quality_report={"review": "source_grounded", "origin": "auto_seed_opec"},
                            hash_norm=str(uuid.uuid4())
                        )
                        db.add(new_q)
                    
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"Error generating case {case_number}: {e}")
                    status.error(f"No se pudo guardar el caso {case_number}: {e}")
            
            current_step += 1
            progress.progress(25, text="Casos generados. Iniciando preguntas funcionales...")
            
            # 2. Functional Questions
            status.info("Clasificando funciones y construyendo los tres niveles de dificultad...")
            func_text = (
                f"Cargo: {active_opec.job_title}\nPropósito: {active_opec.purpose}\n"
                f"Funciones: {str(active_opec.functions)}\nRequisitos: {active_opec.requirements}"
            )
            existing_progressive = db.query(Question).filter(
                Question.competition_id == selected_competition_id,
                Question.case_id.is_(None),
                Question.source_refs.contains("guía oficial pendiente"),
            ).count()
            from core.question_banks.opec_progressive import build_progressive_bank
            q_func = [] if existing_progressive else build_progressive_bank(
                active_opec, getattr(selected_competition, "code", "")
            )
            
            for q in q_func:
                new_q = Question(
                    competition_id=selected_competition_id,
                    question_id=str(uuid.uuid4()),
                    stem=q.get("stem"),
                    options_json=q.get("options"),
                    correct_key=q.get("correct_key"),
                    rationale=q.get("rationale"),
                    track=q.get("track", "FUNCIONAL"),
                    topic=q.get("topic", active_opec.job_title),
                    competency=q.get("competency", "Funcional"),
                    micro_competencia=q.get("competency", "Conocimientos Técnicos"),
                    macro_dominio="Función OPEC" if q.get("track") == "FUNCIONAL" else "Competencias transversales",
                    difficulty=q.get("difficulty", 1),
                    source_refs=q.get("source_refs"),
                    is_verified=False,
                    quality_report={"origin": "progressive_opec_local", "guide_status": "pending"},
                    hash_norm=str(uuid.uuid4())
                )
                db.add(new_q)
            db.commit()
            
            current_step += 1
            progress.progress(50, text="Preguntas funcionales listas. Pasando a comportamentales...")
            
            # 3. Behavioral Questions
            status.info("Generando preguntas comportamentales...")
            behav_text = f"CONTEXTO COMPORTAMENTAL: Generar preguntas sobre Liderazgo, Trabajo en Equipo y Orientación al Resultado para el cargo {active_opec.job_title}."
            existing_behavioral = db.query(Question).filter(
                Question.competition_id == selected_competition_id,
                Question.track == "COMPORTAMENTAL",
            ).count()
            behavioral_needed = max(0, 20 - existing_behavioral)
            try:
                q_behav = gen.generate_from_text(
                    behav_text, count=behavioral_needed, difficulty=2, user_id=u_id
                ) if behavioral_needed and gen is not None else []
            except Exception as exc:
                status.info("Cuota de IA no disponible; completando preguntas comportamentales localmente.")
                print(f"Behavioral AI fallback: {exc}")
                q_behav = build_fallback_questions(
                    active_opec, "COMPORTAMENTAL", behavioral_needed, existing_behavioral
                )
            
            for q in q_behav:
                new_q = Question(
                    competition_id=selected_competition_id,
                    question_id=str(uuid.uuid4()),
                    stem=q.get("stem"),
                    options_json=q.get("options"),
                    correct_key=q.get("correct_key"),
                    rationale=q.get("rationale"),
                    track="COMPORTAMENTAL",
                    topic="Competencias Blandas",
                    competency="Comportamental",
                    micro_competencia="Liderazgo/Trabajo en Equipo",
                    macro_dominio="Competencias Comunes",
                    difficulty=2,
                    hash_norm=str(uuid.uuid4())
                )
                db.add(new_q)
            db.commit()
            
            current_step += 1
            progress.progress(75, text="Ya casi... Generando integridad...")
            
            # 4. Integrity Questions
            status.info("Generando preguntas de valores e integridad...")
            int_text = f"CONTEXTO ÉTICO: Dilemas éticos, Código de Integridad del Servicio Público y valores para un servidor público territorial en el cargo {active_opec.job_title}."
            existing_integrity = db.query(Question).filter(
                Question.competition_id == selected_competition_id,
                Question.competency.like("Integridad%"),
            ).count()
            integrity_needed = max(0, 11 - existing_integrity)
            try:
                q_int = gen.generate_from_text(
                    int_text, count=integrity_needed, difficulty=2, user_id=u_id
                ) if integrity_needed and gen is not None else []
            except Exception as exc:
                status.info("Cuota de IA no disponible; completando integridad y valores localmente.")
                print(f"Integrity AI fallback: {exc}")
                q_int = build_fallback_questions(
                    active_opec, "INTEGRIDAD", integrity_needed, existing_integrity
                )
             
            for q in q_int:
                new_q = Question(
                    competition_id=selected_competition_id,
                    question_id=str(uuid.uuid4()),
                    stem=q.get("stem"),
                    options_json=q.get("options"),
                    correct_key=q.get("correct_key"),
                    rationale=q.get("rationale"),
                    track="COMPORTAMENTAL", # Integrity usually falls here or new track
                    topic="Integridad y Valores",
                    competency="Ética",
                    micro_competencia="Integridad",
                    macro_dominio="Valores DIAN",
                    difficulty=2,
                    hash_norm=str(uuid.uuid4())
                )
                db.add(new_q)
            db.commit()
            
            progress.progress(100, text="¡Proceso Finalizado!")
            status.success("✅ Base inicial generada con éxito. ¡Ya puedes ir al Simulacro tipo examen!")
            st.balloons()
            
            status.success("✅ Base inicial generada con éxito. ¡Ya puedes ir al Simulacro tipo examen!")
            st.balloons()
            
        except Exception as e:
            st.error(f"Error crítico en Auto-Seed: {e}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()

st.divider()
st.caption("🔒 Los datos de tu OPEC se guardan de forma segura en tu base de datos para que la IA los use al generar simulacros.")
