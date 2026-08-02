"""Tax refund and compensation GOA cases for OPEC 236769.

The legal references were checked against the DIAN Tax Statute compilation
available on 2026-08-01 and the DIAN Concept 003312 (int. 280) of 2026.
"""


def q(stem, a, b, c, rationale, articles, extra_source=""):
    source = (
        f"Estatuto Tributario, artículo(s) {articles} "
        "(Compilación Jurídica DIAN, consulta 2026-08-01)."
    )
    if extra_source:
        source = f"{source} {extra_source}"
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": source,
    }


CURATED_GAP_CASES_PHASE11 = [
    {
        "id": "goa-236769-devoluciones-terminos-compensacion-01",
        "title": "Solicitud oportuna y compensación previa a la devolución",
        "topic": "Devoluciones tributarias - oportunidad, término y compensación",
        "difficulty": 3,
        "text": (
            "Una sociedad radica en debida forma una solicitud de devolución de un saldo a favor de "
            "renta veintidós meses después del vencimiento del plazo para declarar. La dependencia "
            "comprueba que el saldo no ha sido devuelto, compensado ni imputado antes, pero encuentra "
            "una obligación tributaria de plazo vencido a cargo de la solicitante. La petición no se "
            "presentó dentro de los dos meses siguientes a la declaración ni a una corrección."
        ),
        "questions": [
            q(
                "¿La solicitud fue presentada dentro de la oportunidad legal para pedir la devolución?",
                "Sí, porque se radicó antes de cumplirse dos años desde el vencimiento del término para declarar.",
                "No, porque toda devolución debe pedirse dentro de los seis meses siguientes a la declaración.",
                "No, porque la existencia de una deuda vencida extingue automáticamente el saldo a favor.",
                "La solicitud de devolución de saldos a favor puede presentarse hasta dos años después del vencimiento del término para declarar; una deuda vencida se atiende mediante compensación previa y no convierte por sí sola la petición en extemporánea.",
                "854 y 861",
            ),
            q(
                "¿Cuál es el término general para efectuar esta devolución, contado desde la solicitud oportuna y en debida forma?",
                "Cincuenta días, sin perjuicio de las compensaciones previas a que haya lugar.",
                "Quince días, porque ese es el término aplicable a toda devolución sin excepción.",
                "Noventa días adicionales en todos los casos, aunque no se ordene investigación previa.",
                "El término general es de cincuenta días desde la solicitud presentada oportunamente y en debida forma. El mes adicional previsto para solicitudes formuladas dentro de los dos meses siguientes a la declaración o su corrección no aplica al caso descrito.",
                "855",
            ),
            q(
                "¿Cómo debe tratarse la obligación tributaria vencida antes de entregar el remanente del saldo a favor?",
                "Compensarla en el mismo acto que ordene la devolución y devolver únicamente el remanente procedente.",
                "Ignorarla y devolver primero la totalidad, porque compensar exige otra solicitud del contribuyente.",
                "Rechazar definitivamente toda la solicitud, aunque el saldo a favor supere la deuda vencida.",
                "Las deudas y obligaciones tributarias de plazo vencido se compensan previamente en el mismo acto que ordena la devolución; la existencia de esa compensación no elimina el derecho sobre el remanente procedente.",
                "855 y 861",
            ),
        ],
    },
    {
        "id": "goa-236769-devoluciones-inadmision-suspension-01",
        "title": "Subsanación formal e investigación previa del saldo solicitado",
        "topic": "Devoluciones tributarias - inadmisión y suspensión de términos",
        "difficulty": 3,
        "text": (
            "Una solicitud de devolución de IVA fue presentada dentro del término legal, pero omite "
            "uno de los documentos formales exigidos. Al revisar la información disponible, el equipo "
            "también detecta que una retención incluida en el saldo podría no haber sido practicada y "
            "que el agente retenedor informado quizá no existe. Un funcionario propone rechazar "
            "definitivamente toda la petición y suspender el trámite por tiempo indefinido."
        ),
        "questions": [
            q(
                "¿Qué decisión corresponde inicialmente por la falta del documento formal exigido?",
                "Inadmitir la solicitud mediante la causal legal aplicable, para permitir su subsanación.",
                "Rechazarla definitivamente, porque toda omisión documental extingue el saldo a favor.",
                "Aprobarla sin verificar requisitos, porque fue presentada dentro de los dos años.",
                "La falta de requisitos formales es causal de inadmisión, no de rechazo definitivo. Además, las causales de inadmisión y rechazo son taxativas y no pueden ampliarse por criterio del funcionario.",
                "857",
                "DIAN, Concepto 003312 (int. 280) de 2026, numerales 4 a 8.",
            ),
            q(
                "Notificado oportunamente el auto inadmisorio, ¿qué oportunidad tiene la solicitante para corregir la omisión?",
                "Presentar una nueva solicitud subsanada dentro del mes siguiente a la inadmisión.",
                "Esperar obligatoriamente un año antes de formular una nueva petición.",
                "Interponer una nueva declaración sin aportar el documento omitido.",
                "El auto inadmisorio debe dictarse, por regla general, dentro de quince días y el solicitante dispone del mes siguiente para presentar una nueva solicitud que subsane la causal; presentada dentro de ese mes conserva la oportunidad aun si entretanto venció el término para solicitar.",
                "857, parágrafo 1, y 858",
            ),
            q(
                "Una vez subsanada la petición, ¿cómo puede procederse frente a los indicios sobre la retención inexistente?",
                "Suspender motivadamente el término hasta por noventa días para que Fiscalización adelante la investigación correspondiente.",
                "Suspenderlo indefinidamente sin acto ni causal, hasta que el contribuyente renuncie al saldo.",
                "Ordenar la devolución total porque una retención informada nunca puede ser verificada.",
                "La posible inexistencia de una retención o del agente retenedor es una causal expresa de investigación previa. La suspensión no es automática ni indefinida: su máximo es de noventa días y debe estar sustentada en los hechos verificados.",
                "856 y 857-1, numeral 1",
                "DIAN, Concepto 003312 (int. 280) de 2026, numerales 10 a 13.",
            ),
        ],
    },
    {
        "id": "goa-236769-devoluciones-investigacion-sancion-01",
        "title": "Resultado de la investigación y devolución improcedente",
        "topic": "Devoluciones tributarias - investigación previa y sanción",
        "difficulty": 3,
        "text": (
            "Durante la investigación previa de una solicitud de devolución de IVA por 300 millones "
            "de pesos, Fiscalización formula requerimiento especial y plantea un saldo a favor de 180 "
            "millones. Esa suma es devuelta. Más adelante, una liquidación oficial determina que el "
            "saldo procedente era de 100 millones, por lo que hubo una devolución en exceso de 80 "
            "millones. El expediente también contiene indicios de que se usaron documentos falsos para "
            "obtener parte de la devolución."
        ),
        "questions": [
            q(
                "Al concluir la investigación previa con requerimiento especial, ¿qué tratamiento correspondía a la solicitud original?",
                "Devolver únicamente el saldo a favor planteado en el requerimiento, sin exigir una nueva solicitud por esa suma.",
                "Devolver los 300 millones solicitados y discutir la diferencia solo después del pago.",
                "Archivar definitivamente todo el trámite, incluso respecto del saldo aceptado por Fiscalización.",
                "Cuando la investigación previa produce requerimiento especial, solo procede la devolución o compensación del saldo a favor planteado en ese acto y no se requiere una nueva solicitud para reconocerlo.",
                "857-1",
            ),
            q(
                "Confirmada oficialmente la devolución en exceso de 80 millones, ¿cuál es la consecuencia ordinaria prevista por el Estatuto?",
                "Reintegrar los 80 millones con los intereses moratorios correspondientes y aplicar una multa del veinte por ciento sobre el exceso determinado por la Administración.",
                "Conservar el exceso porque la devolución inicial constituyó un reconocimiento definitivo e inmodificable.",
                "Pagar únicamente una multa del diez por ciento, sin reintegro ni intereses, aunque la Administración modificó el saldo.",
                "La devolución no es un reconocimiento definitivo. Si una liquidación oficial rechaza o modifica el saldo, se reintegra el exceso con intereses y la sanción ordinaria es del veinte por ciento del valor devuelto o compensado en exceso; el diez por ciento corresponde a la corrección del propio contribuyente.",
                "670, incisos 1 a 5",
            ),
            q(
                "Si se demuestra que la devolución improcedente fue obtenida mediante documentos falsos, ¿qué actuación adicional procede?",
                "Imponer además una sanción del ciento por ciento del monto obtenido fraudulentamente, previa formulación de pliego de cargos con un mes para responder.",
                "Sustituir todas las consecuencias por una amonestación sin oportunidad de defensa.",
                "Duplicar automáticamente los intereses, sin pliego de cargos ni resolución sancionatoria.",
                "El uso de documentos falsos o fraude genera, además de las consecuencias ordinarias, una sanción del ciento por ciento del monto improcedente. Antes de imponerla debe trasladarse el pliego de cargos por un mes para garantizar la defensa.",
                "670, incisos 7 y 9",
            ),
        ],
    },
]
