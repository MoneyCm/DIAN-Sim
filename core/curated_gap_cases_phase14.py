"""GOA cases for OPEC 236769 functions F4 and F9.

The cases exercise the preparation of proposals for management-level meetings
and the technical/legal review of files. Sources were checked in the DIAN public
master-document list and legal compilation on 2026-08-01.
"""


def q(stem, a, b, c, rationale, source):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": source,
    }


F4_SOURCE = (
    "DIAN, ficha de empleo AT-FL-3006 Gestor III, función de organización de información y "
    "propuestas; procedimiento PR-COA-0501 Auditoría Posterior al Despacho, versión 1, y "
    "OD-COA-0006 Guía de Implementación APD (Listado Maestro de Documentos, consulta 2026-08-01)."
)

LP_SOURCE = (
    "DIAN, procedimiento PR-COT-0432 Liquidación Provisional, versión 3, vigente desde "
    "2025-02-24 (Listado Maestro de Documentos, consulta 2026-08-01)."
)


CURATED_GAP_CASES_PHASE14 = [
    {
        "id": "goa-236769-f4-propuesta-apd-directivo-01",
        "title": "Preparación de una propuesta de auditoría para decisión directiva",
        "topic": "F4 - Organización de información y propuestas de fiscalización",
        "difficulty": 3,
        "text": (
            "Una Dirección Seccional identifica operaciones aduaneras que podrían justificar una "
            "Auditoría Posterior al Despacho. Para presentarlas remite una hoja de cálculo con datos "
            "aislados, pero no incorpora el análisis de patrones de comportamiento ni el acta firmada "
            "de la Reunión de Nivel Directivo Local. El gestor considera completar por su cuenta la "
            "decisión de apertura y comunicar que el caso ya fue aprobado."
        ),
        "questions": [
            q(
                "¿Qué debe hacerse antes de tramitar la propuesta incompleta para aprobación?",
                "Devolverla para complementación o corrección, identificando la información mínima y los soportes faltantes.",
                "Declararla aprobada porque una hoja de cálculo reemplaza el análisis y el acta.",
                "Abrir el expediente y reconstruir los soportes únicamente después de finalizar la auditoría.",
                "El procedimiento dispone que las propuestas que no contengan la información mínima requerida deben devolverse para complementación o corrección; organizar información no autoriza a suplir soportes inexistentes.",
                F4_SOURCE,
            ),
            q(
                "¿Qué soporte sustantivo debe acompañar la propuesta local de Auditoría Posterior al Despacho?",
                "El análisis de identificación de patrones exigido por la guía y el acta de la Reunión de Nivel Directivo Local debidamente firmada.",
                "Una afirmación del gestor sin fuentes ni constancia de la reunión local.",
                "La resolución sancionatoria definitiva, aun cuando la auditoría todavía no se ha iniciado.",
                "La guía exige que la propuesta contenga el análisis de patrones de comportamiento y el acta de la reunión local; esos documentos permiten evaluar la propuesta de forma trazable.",
                F4_SOURCE,
            ),
            q(
                "Una vez organizada y presentada la información, ¿quién adopta la decisión final sobre aprobar o rechazar esta propuesta local?",
                "La Subdirección de Fiscalización Aduanera, después de analizar el cumplimiento de los requisitos de la propuesta.",
                "El gestor que consolidó la información, sin revisión de otra instancia.",
                "El usuario aduanero que eventualmente sería auditado.",
                "La función del gestor es organizar y proponer. En el flujo APD, la Subdirección de Fiscalización Aduanera analiza la propuesta local y decide su aprobación o rechazo, dejando las razones correspondientes.",
                F4_SOURCE,
            ),
        ],
    },
    {
        "id": "goa-236769-f9-revision-liquidacion-provisional-01",
        "title": "Revisión formal y técnica de una liquidación provisional",
        "topic": "F9 - Revisión técnica y jurídica de expedientes",
        "difficulty": 3,
        "text": (
            "En un expediente tributario asignado conforme a la competencia funcional, el auditor "
            "proyecta una liquidación provisional. Los cálculos coinciden con los soportes, pero el "
            "proyecto omite el período gravable, el NIT del sujeto obligado y la explicación sumaria "
            "de las modificaciones. El revisor recibe el documento antes de su aprobación y firma."
        ),
        "questions": [
            q(
                "¿Cuál es la actuación correcta del revisor frente a las omisiones detectadas?",
                "Formular observaciones y devolver el proyecto para que sea ajustado antes de otorgar el visto bueno.",
                "Dar visto bueno porque la coincidencia aritmética vuelve innecesarios los requisitos formales.",
                "Notificar el borrador y pedir al contribuyente que complete los datos omitidos.",
                "El control previsto por PR-COT-0432 exige que, si la revisión encuentra inconsistencias, se formulen observaciones y el proyecto regrese a la actividad de elaboración para ajuste.",
                LP_SOURCE,
            ),
            q(
                "¿Por qué las omisiones impiden considerar completo el acto, aunque sus cifras sean correctas?",
                "Porque la liquidación debe identificar período y sujeto, expresar las bases y montos y explicar sumariamente las modificaciones, además de cumplir con firma o sello.",
                "Porque todo acto tributario debe incluir una confesión del sujeto investigado.",
                "Porque la única exigencia de una liquidación provisional es indicar una suma global.",
                "La revisión técnica y jurídica comprende los elementos obligatorios del acto, no solo la operación matemática. El procedimiento enumera fecha, período, nombre o razón social, NIT, bases, montos, explicación y firma o sello.",
                f"{LP_SOURCE} Estatuto Tributario, artículos 712 y 764.",
            ),
            q(
                "Corregido el proyecto y otorgado el visto bueno, ¿cuál es la secuencia de control que corresponde antes de incorporarlo como acto notificado?",
                "Remitirlo para aprobación y firma; solo después gestionar la notificación e incorporar su soporte al expediente.",
                "Permitir que el revisor lo notifique sin aprobación ni firma para ahorrar tiempo.",
                "Archivar el proyecto revisado sin comunicarlo al sujeto obligado.",
                "PR-COT-0432 separa elaboración, revisión, aprobación y firma, y luego la gestión de notificación. El soporte que acredita la entrega debe incorporarse al expediente.",
                LP_SOURCE,
            ),
        ],
    },
    {
        "id": "goa-236769-f9-revision-expediente-decision-01",
        "title": "Control probatorio, correspondencia y término de la decisión",
        "topic": "F9 - Revisión jurídica, probatoria y de términos",
        "difficulty": 3,
        "text": (
            "Una liquidación provisional que hizo las veces de requerimiento especial fue rechazada "
            "por el contribuyente. Este aportó oportunamente documentos para controvertir las glosas. "
            "El proyecto de liquidación oficial de revisión no analiza esas pruebas e incorpora una "
            "glosa nueva que nunca figuró en la liquidación provisional. Faltan pocos días para que "
            "venza el término de dos meses previsto para ratificarla."
        ),
        "questions": [
            q(
                "¿Qué debe exigir el revisor respecto de los documentos aportados por el contribuyente?",
                "Que sean incorporados y valorados y que la conclusión se funde en los hechos demostrados en el expediente.",
                "Que se excluyan sin análisis porque contradicen la hipótesis inicial del auditor.",
                "Que se valoren únicamente después de ejecutoriado el acto definitivo.",
                "Las decisiones tributarias deben apoyarse en hechos probados y en pruebas que obren oportunamente en el expediente; la revisión no puede convalidar una conclusión que omite evidencia pertinente.",
                f"Estatuto Tributario, artículos 742 y 744 (Compilación Jurídica DIAN, consulta 2026-08-01). {LP_SOURCE}",
            ),
            q(
                "¿Puede mantenerse en la liquidación oficial la glosa nueva que no fue planteada en el acto previo?",
                "No; debe observarse por falta de correspondencia y ajustarse el proyecto al marco fáctico comunicado previamente al contribuyente.",
                "Sí; la liquidación oficial puede cambiar completamente los hechos sin oportunidad previa de defensa.",
                "Sí, siempre que la nueva glosa aumente el recaudo esperado.",
                "La liquidación de revisión debe contraerse a la declaración y a los hechos contemplados en el requerimiento o su ampliación. Cuando la liquidación provisional cumple esa función, la ratificación debe respetar ese marco y motivar la decisión.",
                f"Estatuto Tributario, artículos 711, 712 y 764-6 (Compilación Jurídica DIAN, consulta 2026-08-01). {LP_SOURCE}",
            ),
            q(
                "Ante la proximidad del vencimiento, ¿cómo debe conciliarse el control de calidad con el término para decidir?",
                "Emitir de inmediato observaciones para corregir, revisar y someter el acto a aprobación y firma dentro del término, sin omitir controles ni alterar fechas.",
                "Aprobar el acto defectuoso y corregir la motivación después de notificarlo.",
                "Modificar la fecha del documento para aparentar que fue expedido oportunamente.",
                "El procedimiento exige ratificar mediante liquidación oficial de revisión dentro de los dos meses siguientes al agotamiento del término de respuesta y conserva las etapas de revisión, aprobación, firma y notificación; la urgencia no elimina esos controles.",
                f"{LP_SOURCE} Estatuto Tributario, artículo 764-6.",
            ),
        ],
    },
]
