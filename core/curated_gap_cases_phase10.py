"""Tax due-process GOA cases grounded in the current Colombian Tax Statute."""


def q(stem, a, b, c, rationale, articles):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": (
            f"Estatuto Tributario, artículo(s) {articles} "
            "(Compilación Jurídica DIAN, consulta 2026-08-01)."
        ),
    }


CURATED_GAP_CASES_PHASE10 = [
    {
        "id": "goa-236769-tributario-requerimiento-respuesta-01",
        "title": "Preparación y respuesta de un requerimiento especial",
        "topic": "Debido proceso tributario - requerimiento especial y respuesta",
        "difficulty": 3,
        "text": (
            "Al revisar la declaración de renta de una sociedad, el equipo propone desconocer parte de "
            "los costos y aumentar una sanción. El borrador del requerimiento solo enumera las glosas, "
            "sin explicar sus razones ni cuantificar los mayores valores. Un funcionario sugiere omitir "
            "el requerimiento y expedir directamente la liquidación de revisión."
        ),
        "questions": [
            q(
                "¿Qué actuación debe realizarse antes de expedir una eventual liquidación de revisión?",
                "Notificar por una sola vez un requerimiento especial que incluya todos los puntos que se pretende modificar y las razones que los sustentan.",
                "Expedir de inmediato la liquidación, porque el requerimiento es opcional cuando existen diferencias contables.",
                "Enviar varios requerimientos sucesivos hasta que el contribuyente acepte las glosas.",
                "El requerimiento especial es un requisito previo de la liquidación de revisión y debe presentar, por una sola vez, la totalidad de los puntos propuestos y su motivación.",
                "703",
            ),
            q(
                "¿Qué falta corregir en el contenido económico del borrador del requerimiento?",
                "Cuantificar los impuestos, anticipos, retenciones y sanciones que se pretende adicionar a la liquidación privada.",
                "Suprimir toda cifra para reservar la cuantificación hasta la decisión definitiva.",
                "Incluir únicamente el valor de los costos declarados, aunque no muestre los mayores tributos o sanciones propuestos.",
                "El requerimiento debe permitir conocer el alcance económico de la modificación propuesta mediante la cuantificación exigida por el Estatuto Tributario.",
                "704",
            ),
            q(
                "Una vez notificado correctamente el requerimiento, ¿qué oportunidad debe respetarse al contribuyente?",
                "Tres meses para presentar objeciones escritas, solicitar pruebas conducentes, subsanar omisiones permitidas y pedir documentos o inspecciones pertinentes.",
                "Cinco días para aceptar integralmente las glosas, sin posibilidad de solicitar pruebas.",
                "Seis meses para interponer reconsideración contra el requerimiento antes de responderlo.",
                "La respuesta al requerimiento es la oportunidad de contradicción: corre por tres meses desde su notificación y permite formular objeciones y ejercer las facultades probatorias previstas por la ley.",
                "707",
            ),
        ],
    },
    {
        "id": "goa-236769-tributario-ampliacion-01",
        "title": "Nuevos hallazgos después de la respuesta al requerimiento",
        "topic": "Debido proceso tributario - ampliación del requerimiento especial",
        "difficulty": 3,
        "text": (
            "El contribuyente responde oportunamente un requerimiento especial relacionado con ingresos "
            "omitidos. Al valorar la respuesta, la dependencia identifica una deducción soportada en una "
            "operación diferente que no fue incluida en el requerimiento inicial. El equipo quiere agregar "
            "este nuevo hecho directamente a la liquidación y conceder quince días para controvertirlo."
        ),
        "questions": [
            q(
                "¿Cuál es la vía procedente para incorporar el nuevo hecho al proceso de determinación?",
                "Ordenar, por una sola vez y dentro del término legal, una ampliación del requerimiento que incluya el nuevo hecho y la determinación oficial propuesta.",
                "Agregarlo por primera vez en la liquidación de revisión, sin actuación previa de contradicción.",
                "Formular un segundo requerimiento especial autónomo por la misma declaración.",
                "La ampliación puede incluir hechos y conceptos no contemplados inicialmente y una nueva determinación, preservando la oportunidad de defensa antes de la liquidación.",
                "708",
            ),
            q(
                "¿Hasta cuándo puede ordenarse válidamente esa ampliación?",
                "Dentro de los tres meses siguientes al vencimiento del plazo otorgado para responder el requerimiento inicial.",
                "En cualquier momento posterior a la liquidación de revisión, mientras no se haya pagado el mayor impuesto.",
                "Solo durante los tres días siguientes a la respuesta efectivamente presentada por el contribuyente.",
                "El término para ordenar la ampliación se cuenta desde el vencimiento del plazo para responder el requerimiento, no desde la fecha en que el contribuyente decida presentar su respuesta.",
                "708",
            ),
            q(
                "¿Es válido conceder quince días para responder la ampliación?",
                "No; el plazo fijado para responderla no puede ser inferior a tres meses ni superior a seis meses.",
                "Sí; toda ampliación se responde obligatoriamente dentro de quince días calendario.",
                "Sí; al tratarse de un hecho nuevo la Administración puede eliminar por completo el plazo de respuesta.",
                "El Estatuto establece expresamente un intervalo de tres a seis meses para la respuesta a la ampliación, por lo que quince días desconocería esa garantía.",
                "708",
            ),
        ],
    },
    {
        "id": "goa-236769-tributario-correspondencia-liquidacion-01",
        "title": "Control de correspondencia y contenido de la liquidación de revisión",
        "topic": "Debido proceso tributario - liquidación de revisión",
        "difficulty": 3,
        "text": (
            "El requerimiento especial propuso modificar ingresos y costos; una ampliación posterior "
            "incorporó una sanción vinculada con esos hallazgos. Al proyectar la liquidación de revisión, "
            "el equipo agrega una glosa basada en una operación distinta que nunca figuró en esos actos. "
            "Además, el proyecto omite las bases de cuantificación y la explicación de los cambios."
        ),
        "questions": [
            q(
                "¿Puede mantenerse en la liquidación la glosa sobre la operación que no apareció en el requerimiento ni en su ampliación?",
                "No; debe excluirse porque la liquidación solo puede referirse a la declaración y a los hechos contemplados previamente en esos actos.",
                "Sí; la liquidación puede introducir cualquier hecho nuevo sin posibilidad previa de contradicción.",
                "Sí; basta con que la glosa nueva aumente el impuesto determinado por la dependencia.",
                "El principio de correspondencia delimita la liquidación de revisión a los hechos anunciados en el requerimiento especial o en su ampliación y protege el derecho de defensa.",
                "711",
            ),
            q(
                "Si existe mérito para decidir, ¿cuál es el término general para notificar la liquidación de revisión?",
                "Seis meses contados desde el vencimiento del término para responder el requerimiento especial o su ampliación, según corresponda.",
                "Tres años contados siempre desde la fecha de expedición del requerimiento, sin considerar la respuesta.",
                "Quince días contados desde la presentación efectiva de cualquier escrito del contribuyente.",
                "La regla vigente fija seis meses desde el vencimiento de la oportunidad de respuesta aplicable; las suspensiones solo operan en los eventos expresamente previstos por la ley.",
                "710",
            ),
            q(
                "¿Qué debe incorporarse para completar debidamente el proyecto de liquidación?",
                "Las bases de cuantificación, los tributos y sanciones a cargo y una explicación sumaria de las modificaciones, junto con los demás datos y formalidades legales.",
                "Solo el nombre del contribuyente y el total a pagar, sin indicar cómo se obtuvo.",
                "Únicamente una remisión genérica al requerimiento, sin periodo, identificación ni explicación de las modificaciones.",
                "La liquidación debe identificar el acto y al contribuyente, mostrar las bases y montos determinados, explicar sumariamente las modificaciones y contener la firma o control correspondiente.",
                "712",
            ),
        ],
    },
]
