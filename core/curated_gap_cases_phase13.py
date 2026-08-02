"""Current tax-notification and administrative-review GOA cases for OPEC 236769."""


def q(stem, a, b, c, rationale, source):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": source,
    }


ET = "Estatuto Tributario, artículo(s) {articles} (Compilación Jurídica DIAN, consulta 2026-08-01)."


CURATED_GAP_CASES_PHASE13 = [
    {
        "id": "goa-236769-tributario-notificacion-formas-direccion-01",
        "title": "Selección del medio y la dirección para notificar actos tributarios",
        "topic": "Procedimiento tributario - formas y dirección de notificación",
        "difficulty": 3,
        "text": (
            "Durante un proceso de determinación, una sociedad señala expresamente una dirección "
            "procesal física y otra electrónica. La dependencia debe notificar un requerimiento especial "
            "y, más adelante, la providencia que decida un recurso. El equipo propone utilizar para todos "
            "los actos una publicación general, pese a que dispone de las direcciones informadas."
        ),
        "questions": [
            q(
                "¿Cuáles son las formas previstas para notificar el requerimiento especial?",
                "De manera electrónica, personalmente o mediante la red oficial de correos o un servicio de mensajería especializada autorizado.",
                "Exclusivamente mediante publicación general, aunque exista una dirección válida informada.",
                "Únicamente por llamada telefónica sin entrega ni puesta en conocimiento del acto.",
                "Los requerimientos, inspecciones, emplazamientos, liquidaciones y demás actuaciones comprendidas por la norma deben notificarse mediante alguna de las formas expresamente autorizadas.",
                ET.format(articles="565"),
            ),
            q(
                "¿Puede emplearse la dirección procesal expresamente indicada por la sociedad?",
                "Sí; los actos del proceso de determinación y discusión pueden notificarse física o electrónicamente a la dirección procesal señalada expresamente.",
                "No; la dirección procesal carece de efectos y siempre debe ignorarse frente a cualquier otra dirección.",
                "Solo después de terminar el proceso, porque durante la determinación no puede informarse una dirección procesal.",
                "La dirección procesal es aplicable a decisiones y actos del proceso de determinación y discusión; su modalidad electrónica opera preferentemente una vez implementada por la DIAN.",
                ET.format(articles="564"),
            ),
            q(
                "Si la providencia que decide el recurso no se notifica electrónicamente, ¿qué regla especial debe aplicar la dependencia?",
                "Intentar la notificación personal y acudir al edicto si el interesado no comparece dentro de los diez días contados desde el día siguiente al envío del aviso de citación.",
                "Notificarla únicamente por estado, sin citar previamente al interesado.",
                "Aplicar siempre la publicación en periódico como primera y única alternativa.",
                "Las providencias que deciden recursos tienen regla especial: notificación personal o, ante la falta de comparecencia en el término legal, por edicto; también admite la vía electrónica.",
                ET.format(articles="565"),
            ),
        ],
    },
    {
        "id": "goa-236769-tributario-notificacion-electronica-01",
        "title": "Fecha de notificación electrónica e inicio del término de defensa",
        "topic": "Procedimiento tributario - notificación electrónica",
        "difficulty": 3,
        "text": (
            "La DIAN envía una liquidación oficial al correo electrónico autorizado de un contribuyente "
            "el 6 de agosto y el sistema registra su entrega el 7 de agosto. Una ficha antigua del banco "
            "afirma que la notificación solo se surte cinco días después de la entrega y confunde ese "
            "momento con el inicio del plazo para responder o impugnar."
        ),
        "questions": [
            q(
                "Según el artículo 566-1 vigente, ¿en qué fecha se entiende surtida la notificación electrónica?",
                "En la fecha del envío del acto al correo electrónico autorizado, es decir, el 6 de agosto.",
                "Cinco días después de su entrega, porque ese periodo determina la fecha de notificación.",
                "Solo cuando el contribuyente abra voluntariamente el archivo adjunto.",
                "La regla histórica del banco es incorrecta: la notificación se entiende surtida en la fecha del envío; el periodo posterior de cinco días protege el inicio del término de defensa y no cambia esa fecha.",
                ET.format(articles="566-1"),
            ),
            q(
                "¿Cuándo comienza a correr el término legal del contribuyente para responder o impugnar?",
                "Una vez hayan transcurrido cinco días a partir de la entrega del correo electrónico, sin confundir ese periodo con la fecha de notificación.",
                "El mismo día del envío, porque la ley no concede ningún periodo previo al término de defensa.",
                "Cinco días antes de la entrega registrada por el sistema.",
                "El artículo distingue los dos hitos: la notificación se surte con el envío y el término del administrado comienza después de transcurridos cinco días desde la entrega; la doctrina DIAN vigente cuenta ese periodo desde el día siguiente a la entrega.",
                "Estatuto Tributario, artículo 566-1; DIAN, Concepto 018477 de 2025 y Concepto 006682 de 2026 (consulta 2026-08-01).",
            ),
            q(
                "Si el contribuyente no puede acceder al contenido por una falla tecnológica, ¿cómo debe actuar?",
                "Informarlo a la DIAN dentro de los tres días siguientes a la entrega para que el acto sea reenviado una sola vez, conservando las reglas legales sobre notificación e inicio de términos.",
                "Esperar hasta el vencimiento del recurso y alegar la falla sin haberla informado.",
                "Solicitar que el acto se elimine definitivamente, pues la DIAN no puede intentar un reenvío.",
                "La imposibilidad de acceso debe comunicarse oportunamente; la DIAN reenvía una vez, la notificación conserva como referencia el primer envío y el término corre después de cinco días desde la entrega efectiva.",
                ET.format(articles="566-1"),
            ),
        ],
    },
    {
        "id": "goa-236769-tributario-reconsideracion-01",
        "title": "Discusión de una liquidación oficial de revisión",
        "topic": "Procedimiento tributario - recurso de reconsideración",
        "difficulty": 3,
        "text": (
            "Después de haber respondido debidamente el requerimiento especial, un contribuyente recibe "
            "una liquidación oficial de revisión y discrepa de las glosas mantenidas. Su asesor prepara "
            "un correo informal sin motivos concretos ni acreditación de representación y sostiene que "
            "puede presentar el recurso ante cualquier dependencia cuando lo considere conveniente."
        ),
        "questions": [
            q(
                "¿Cuál es la regla general para discutir administrativamente la liquidación oficial?",
                "Interponer recurso de reconsideración ante la oficina competente dentro de los dos meses siguientes a la notificación, aplicando las reglas especiales de cómputo si fue electrónica.",
                "Presentar apelación ante cualquier dependencia dentro de los cinco años siguientes.",
                "Formular reposición verbal contra la liquidación sin plazo ni autoridad determinada.",
                "Contra las liquidaciones oficiales procede, como regla general, la reconsideración; el Estatuto fija la autoridad y un término de dos meses, salvo disposición expresa en contrario.",
                ET.format(articles="720 y 566-1"),
            ),
            q(
                "¿Qué debe corregirse para que el recurso cumpla los requisitos generales de procedencia?",
                "Presentarlo por escrito, expresar concretamente los motivos, hacerlo oportunamente y acreditar la personería si actúa un apoderado o representante.",
                "Eliminar los motivos de inconformidad y omitir cualquier prueba de representación.",
                "Limitarse a manifestar desacuerdo verbal, aun después de vencida la oportunidad legal.",
                "El artículo 722 exige escrito con motivos concretos, oportunidad y presentación directa por el legitimado o acreditación de personería cuando actúe por representación.",
                ET.format(articles="722"),
            ),
            q(
                "Dado que atendió debidamente el requerimiento especial, ¿puede el contribuyente prescindir de la reconsideración?",
                "Sí; puede acudir directamente a la jurisdicción contencioso-administrativa dentro de los cuatro meses siguientes a la notificación de la liquidación oficial.",
                "No; la reconsideración es obligatoria sin excepción en toda liquidación oficial.",
                "Sí, pero solo para presentar la demanda diez años después de la notificación.",
                "El parágrafo del artículo 720 permite acudir per saltum a la jurisdicción cuando el requerimiento especial fue atendido en debida forma, dentro de la oportunidad de cuatro meses allí prevista.",
                ET.format(articles="720, parágrafo"),
            ),
        ],
    },
]
