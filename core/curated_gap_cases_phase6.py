"""Source-grounded procedural GOA cases derived from the user's DIAN Drive library."""


def q(stem, a, b, c, rationale, source):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": source,
    }


CURATED_GAP_CASES_PHASE6 = [
    {
        "id": "goa-236769-liquidacion-provisional-flujo-01",
        "title": "Recepción y preparación de una liquidación provisional",
        "topic": "Ejecución de acciones de fiscalización - liquidación provisional",
        "difficulty": 3,
        "text": (
            "Una división recibe, junto con el insumo correspondiente, copia del acta de nivel "
            "directivo que seleccionó un caso para liquidación provisional. El jefe debe asignarlo; "
            "el auditor designado prepara la investigación y, posteriormente, el sujeto obligado "
            "presenta respuesta y solicita la práctica de pruebas pertinentes."
        ),
        "questions": [
            q(
                "¿Qué criterio permite una asignación directa coherente con el procedimiento?",
                "Considerar las características técnicas del insumo, la competencia del servidor, las novedades de personal y su carga de trabajo.",
                "Entregar siempre el expediente al servidor con mayor antigüedad.",
                "Permitir que cada auditor escoja libremente el caso que prefiera.",
                "La asignación directa debe atender el insumo, la competencia laboral, las novedades administrativas y el inventario individual de cargas.",
                "UAE DIAN, procedimiento PR-COT-0432 Liquidación Provisional, versión 3, actividad 2, p. 9.",
            ),
            q(
                "Antes de ejecutar las actividades de auditoría, ¿cómo debe definirse el plan?",
                "Debe ser concertado entre el servidor comisionado y el jefe inmediato o la persona designada para ello.",
                "Debe elaborarlo exclusivamente el sujeto obligado al responder.",
                "Debe copiarse sin ajustes del plan usado en el expediente anterior.",
                "El procedimiento define el plan como un documento de pautas técnicas que debe concertarse con la jefatura o quien sea designado.",
                "UAE DIAN, procedimiento PR-COT-0432 Liquidación Provisional, versión 3, definición de plan de auditoría.",
            ),
            q(
                "El sujeto obligado responde dentro del término y pide una prueba pertinente. ¿Qué tratamiento corresponde?",
                "Incorporar y tramitar la solicitud dentro de la actuación conforme a su pertinencia y al término aplicable.",
                "Rechazarla porque solo la DIAN puede aportar elementos probatorios.",
                "Archivar automáticamente toda la actuación por haberse presentado una respuesta.",
                "La matriz de entradas del procedimiento reconoce que el sujeto obligado puede allegar o solicitar las pruebas que considere pertinentes.",
                "UAE DIAN, procedimiento PR-COT-0432 Liquidación Provisional, versión 3, entrada 12, p. 8.",
            ),
        ],
    },
    {
        "id": "goa-236769-garantia-competencia-01",
        "title": "Insumo aduanero recibido por una dependencia no competente",
        "topic": "Revisión jurídica y actos aduaneros - efectividad de garantías",
        "difficulty": 3,
        "text": (
            "Una dependencia recibe un escrito para declarar el incumplimiento de una obligación "
            "aduanera y hacer efectiva la garantía. Al verificar el insumo establece que una parte "
            "corresponde territorialmente a otra dirección seccional y otra, por competencia funcional, "
            "a una dependencia distinta de la misma seccional. Además, el incumplimiento principal ya "
            "se discute dentro de otro proceso administrativo."
        ),
        "questions": [
            q(
                "¿Cómo debe trasladarse la parte que corresponde territorialmente a otra dirección seccional?",
                "Mediante oficio dirigido a la seccional competente.",
                "Con la planilla de reparto interna de la misma dependencia.",
                "Sin documento, mediante una anotación informal en el expediente.",
                "El procedimiento ordena oficio cuando el traslado obedece a competencia territorial de otra dirección seccional.",
                "UAE DIAN, procedimiento PR-COA-0229, versión 4, numeral 3.1, p. 2.",
            ),
            q(
                "¿Qué instrumento corresponde para la parte de competencia funcional de otra dependencia de la misma seccional?",
                "Formato FT-COA-1232 Planilla Múltiple de Remisión.",
                "Oficio de cobro enviado directamente al garante.",
                "Informe final de auditoría posterior al despacho.",
                "Para traslados funcionales dentro de la misma seccional se utiliza la Planilla Múltiple de Remisión.",
                "UAE DIAN, procedimiento PR-COA-0229, versión 4, numeral 3.1, p. 2.",
            ),
            q(
                "Frente al incumplimiento que ya se discute en otro proceso administrativo, ¿qué verificación es decisiva antes de continuar por este procedimiento?",
                "Confirmar que la efectividad de la garantía no esté condicionada ni sea objeto de discusión en ese otro proceso.",
                "Continuar siempre en paralelo porque ambos procedimientos son acumulables por definición.",
                "Cerrar el otro proceso sin revisar su objeto para conservar este trámite.",
                "El objetivo del PR-COA-0229 limita su aplicación a incumplimientos que no sean objeto de discusión dentro de otro proceso administrativo.",
                "UAE DIAN, procedimiento PR-COA-0229, versión 4, objetivo, p. 1.",
            ),
        ],
    },
    {
        "id": "goa-236769-apd-evidencia-cierre-01",
        "title": "Hallazgos y solicitudes externas en una auditoría posterior al despacho",
        "topic": "Fiscalización aduanera - auditoría posterior al despacho",
        "difficulty": 3,
        "text": (
            "Durante una auditoría posterior al despacho, los funcionarios detectan una posible "
            "controversia de valor y solicitan información al exterior. La respuesta extranjera no llega "
            "en el plazo esperado. Con la información disponible elaboran resultados parciales, "
            "identifican circunstancias del posible incumplimiento y preparan la comunicación al auditado."
        ),
        "questions": [
            q(
                "La respuesta a la solicitud exterior no ha llegado. ¿Qué debe hacer el equipo auditor?",
                "Continuar la auditoría y analizar las demás fuentes disponibles.",
                "Suspender indefinidamente toda actuación hasta recibir respuesta.",
                "Cerrar el caso y declarar cumplidas las obligaciones por falta de respuesta.",
                "El procedimiento indica expresamente que la auditoría continúa independientemente de que se reciba o no respuesta del exterior.",
                "UAE DIAN, procedimiento PR-COA-0501 Auditoría Posterior al Despacho, versión 1, actividades 31 a 35, pp. 14-15.",
            ),
            q(
                "Si la controversia requiere pronunciamiento técnico sobre valor, ¿qué actuación corresponde?",
                "Solicitar el pronunciamiento mediante oficio y el formato FT-COA-2040 con la documentación soporte.",
                "Pedir al auditado que decida por sí mismo el valor definitivo.",
                "Omitir el análisis técnico y pasar directamente al informe final.",
                "Para controversias de valor, subpartida u origen se prevé solicitar pronunciamiento técnico con el formato y soportes definidos.",
                "UAE DIAN, procedimiento PR-COA-0501 Auditoría Posterior al Despacho, versión 1, actividades 32 y 33, p. 14.",
            ),
            q(
                "¿Qué contenido debe asegurar el equipo en el informe preliminar?",
                "Finalidad, objetivos, alcance, resultados, conclusiones, recomendaciones y circunstancias del posible incumplimiento.",
                "Solo una lista de documentos recibidos, sin conclusiones ni recomendaciones.",
                "Una sanción definitiva sin comunicar resultados parciales al superior.",
                "El informe preliminar presenta resultados parciales al superior e identifica modo, tiempo y lugar, además de las acciones recomendadas.",
                "UAE DIAN, procedimiento PR-COA-0501 Auditoría Posterior al Despacho, versión 1, definición de informe preliminar, p. 6.",
            ),
        ],
    },
]
