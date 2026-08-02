"""Current procedural exchange-control GOA cases for OPEC 236769."""


def q(stem, a, b, c, rationale, articles):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": (
            f"Decreto Ley 2245 de 2011, artículo(s) {articles} "
            "(Compilación Jurídica DIAN, consulta 2026-08-01)."
        ),
    }


CURATED_GAP_CASES_PHASE8 = [
    {
        "id": "goa-236769-cambiario-inicio-reserva-01",
        "title": "Inicio, reserva y traslado de una investigación cambiaria",
        "topic": "Fiscalización cambiaria - inicio y manejo del expediente",
        "difficulty": 3,
        "text": (
            "La dependencia recibe de un tercero un informe documentado sobre pagos de una importación "
            "presuntamente realizados por fuera del mercado cambiario. Antes de formular cargos obtiene "
            "documentos bancarios reservados. Durante el análisis también encuentra indicios de una "
            "infracción tributaria distinta de los hechos cambiarios investigados."
        ),
        "questions": [
            q(
                "¿Puede iniciarse la actuación a partir del informe del tercero sin avisar previamente al presunto infractor?",
                "Sí, si el medio ofrece credibilidad; esta etapa puede desarrollarse sin su concurso o conocimiento.",
                "No, porque solo una denuncia firmada por una autoridad permite iniciar la actuación.",
                "No, porque antes de verificar cualquier dato debe formularse el pliego de cargos.",
                "La actuación puede iniciarse de oficio, por informes, traslados, quejas o cualquier medio creíble, sin requerir el conocimiento previo del presunto infractor.",
                "7",
            ),
            q(
                "¿Cómo deben manejarse los documentos bancarios obtenidos para el expediente?",
                "Incorporarlos en cuaderno separado y conservar la reserva legal que los ampara.",
                "Publicarlos con el expediente completo porque la DIAN los obtuvo válidamente.",
                "Excluirlos automáticamente porque la reserva bancaria siempre es oponible a la DIAN.",
                "La reserva bancaria no se opone a la actuación, pero los documentos obtenidos mantienen la reserva legal y deben conformar cuaderno separado.",
                "8",
            ),
            q(
                "¿Qué debe hacerse con los indicios de una posible infracción tributaria encontrados durante la investigación cambiaria?",
                "Enviar copia de los documentos pertinentes a la dependencia competente sin desatender la investigación cambiaria.",
                "Convertir la investigación cambiaria en tributaria y eliminar el expediente original.",
                "Ignorarlos porque una investigación cambiaria no puede generar traslados internos.",
                "El régimen ordena trasladar a la dependencia competente los posibles incumplimientos tributarios o aduaneros detectados en una investigación cambiaria.",
                "10",
            ),
        ],
    },
    {
        "id": "goa-236769-cambiario-visita-prueba-01",
        "title": "Visita cambiaria, competencia y protección de la evidencia",
        "topic": "Fiscalización cambiaria - visita y prueba",
        "difficulty": 3,
        "text": (
            "Un equipo prepara una visita de registro cambiario a las oficinas de una sociedad que "
            "realiza operaciones de cambio. El coordinador del grupo pretende ordenar directamente la "
            "visita. Durante la diligencia se localizan archivos relevantes y dinero puesto a disposición "
            "por otra autoridad que podría estar vinculado con una infracción cambiaria."
        ),
        "questions": [
            q(
                "¿Es suficiente la orden expedida por el coordinador del grupo para realizar una visita que implique registro cambiario?",
                "No; debe ordenarla uno de los funcionarios específicamente habilitados por el decreto.",
                "Sí; cualquier servidor que participe en la visita tiene competencia para ordenarla.",
                "Sí, siempre que la sociedad no conozca previamente la diligencia.",
                "La facultad de ordenar visitas que impliquen registro recae únicamente en el Director de Gestión de Fiscalización, el Subdirector competente o el Director Seccional competente, o quienes hagan sus veces.",
                "9, parágrafo",
            ),
            q(
                "Durante una visita válidamente ordenada, ¿qué puede examinar el equipo para verificar el manejo de las operaciones de cambio?",
                "Oficinas, archivos, muebles y contabilidad relacionados con la verificación, además de solicitar copias pertinentes.",
                "Únicamente la declaración de renta más reciente, sin revisar archivos cambiarios.",
                "Cualquier vivienda de los socios sin orden ni relación con las operaciones investigadas.",
                "Las facultades comprenden el registro y examen de oficinas, archivos, muebles y contabilidad, así como obtener copias de documentos relevantes.",
                "9, numerales 2 a 4",
            ),
            q(
                "¿Qué tratamiento procede frente al dinero puesto a disposición que podría constituir una violación cambiaria?",
                "Retenerlo conforme a la facultad legal y constituir oportunamente el depósito o custodia correspondiente.",
                "Distribuirlo entre las dependencias que participaron en la diligencia.",
                "Devolverlo inmediatamente sin documentarlo porque provino de otra autoridad.",
                "La DIAN puede retener valores vinculados a una posible infracción y debe constituir los comprobantes de depósito o entregarlos en custodia en los términos legales.",
                "9, numeral 6",
            ),
        ],
    },
    {
        "id": "goa-236769-cambiario-cargos-descargos-01",
        "title": "Formulación de cargos y defensa en materia cambiaria",
        "topic": "Fiscalización cambiaria - cargos, descargos y decisión",
        "difficulty": 3,
        "text": (
            "Concluida la etapa previa, la dependencia considera que existen hechos constitutivos de "
            "infracción cambiaria. El proyecto de acto solo identifica al investigado y propone una multa, "
            "sin relacionar las pruebas ni analizar las operaciones. Después de la notificación, el "
            "investigado desea presentar descargos y solicitar pruebas."
        ),
        "questions": [
            q(
                "¿Qué debe corregirse en el proyecto antes de formular los cargos?",
                "Agregar hechos, pruebas, normas presuntamente infringidas, análisis de las operaciones y liquidación de lo investigado.",
                "Eliminar la identificación del investigado para proteger la reserva.",
                "Sustituir la motivación por una referencia genérica a cualquier norma cambiaria.",
                "El acto debe ser motivado e incluir identificación, hechos, pruebas, normas, análisis de operaciones y liquidación en moneda legal colombiana, además de la sanción propuesta.",
                "11",
            ),
            q(
                "¿Qué recurso procede directamente contra el acto de formulación de cargos?",
                "Ninguno; la defensa se ejerce mediante descargos, solicitud o aporte de pruebas y objeción de las obtenidas.",
                "Reconsideración obligatoria antes de presentar descargos.",
                "Apelación ante el Banco de la República.",
                "Contra el acto de formulación de cargos no procede recurso; el traslado permite controvertirlo y ejercer la defensa probatoria.",
                "11 y 21",
            ),
            q(
                "¿Cuándo debe presentar el investigado sus descargos y solicitar o aportar pruebas?",
                "Durante los dos meses de traslado contados desde el día siguiente a la notificación del acto de cargos.",
                "En cualquier momento posterior a la resolución sancionatoria, sin límite temporal.",
                "Antes de que exista el acto de formulación de cargos y como única condición de validez.",
                "El traslado dura dos meses desde el día siguiente a la notificación y constituye la oportunidad para descargos, solicitud o aporte de pruebas y objeciones.",
                "21",
            ),
        ],
    },
]
