"""Inter-dependency evidence and DENFIS GOA cases for OPEC 236769."""


def q(stem, a, b, c, rationale, source):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": source,
    }


PR_COA_0223_INTERNAL = (
    "UAE DIAN, procedimiento PR-COA-0223 Investigación de infracciones cambiarias, "
    "versión 6, pp. 6 y 24-25 (Listado Maestro de Documentos, consulta 2026-08-01)."
)
IN_COT_0083 = (
    "UAE DIAN, instructivo IN-COT-0083 Trámite de las solicitudes de pruebas al exterior, "
    "versión 2, numeral 4.3.1, pp. 5-6 (Listado Maestro de Documentos, consulta 2026-08-01)."
)
DENFIS = (
    "UAE DIAN, manual MN-COT-0043 Manual de usuario DENFIS, sección 5.6; DIAN, página "
    "oficial Denuncias TAC (consulta 2026-08-01)."
)
COMMON_FUNCTIONS = (
    "Resolución DIAN 67 de 2024, artículo 6, numerales 11 y 12 "
    "(Compilación Jurídica DIAN, consulta 2026-08-01)."
)


CURATED_GAP_CASES_PHASE15 = [
    {
        "id": "goa-236769-prueba-interdependencia-01",
        "title": "Prueba practicada por la seccional competente",
        "topic": "Práctica de pruebas - solicitud entre dependencias",
        "difficulty": 3,
        "text": (
            "Una dependencia del nivel central adelanta una investigación cambiaria y necesita "
            "verificar documentos y registros que se encuentran en un establecimiento de Cali. Por "
            "razones de jurisdicción solicita la práctica de la prueba a la dependencia seccional. El "
            "equipo receptor propone hacer una visita informal, examinar asuntos ajenos a lo solicitado "
            "y conservar localmente el resultado sin remitirlo a la dependencia investigadora."
        ),
        "questions": [
            q(
                "¿Cómo debe encauzarse la solicitud de la prueba que se practicará en el país?",
                "Directamente hacia el área o dependencia competente por jurisdicción, identificando la prueba requerida y su relación con la investigación.",
                "Mediante una petición informal al investigado para que decida qué dependencia debe intervenir.",
                "A través del canal reservado para pruebas en el exterior, aunque la diligencia deba realizarse en Cali.",
                "El procedimiento distingue las pruebas internas de las externas: las primeras pueden solicitarse directamente a otra área o dependencia del proceso por razones de jurisdicción y competencia.",
                PR_COA_0223_INTERNAL,
            ),
            q(
                "¿Qué reglas debe observar la dependencia seccional al ejecutar la visita solicitada?",
                "Actuar dentro de los términos y actividades fijados en el Auto Comisorio y consignar los hechos ocurridos en el Acta de Diligencia.",
                "Extender la visita a cualquier asunto no comisionado y omitir el acta si no encuentra una infracción.",
                "Iniciar la diligencia antes de que exista comisión y documentarla únicamente mediante notas personales.",
                "PR-COA-0223 exige que los funcionarios comisionados actúen dentro del Auto Comisorio; al finalizar deben registrar los hechos de la visita en el Acta de Diligencia.",
                PR_COA_0223_INTERNAL,
            ),
            q(
                "Una vez practicada la prueba, ¿qué tratamiento corresponde al resultado?",
                "Remitir a la dependencia solicitante el acta y los soportes obtenidos, conservando su integridad y aplicando los controles de información y gestión documental.",
                "Guardar el resultado exclusivamente en archivos personales del equipo que realizó la visita.",
                "Publicar íntegramente los soportes para demostrar que la diligencia ya terminó.",
                "La prueba se practicó para obrar en la investigación de la dependencia solicitante; el resultado debe quedar documentado y disponible para su incorporación, con protección de datos y adecuada organización y conservación documental.",
                f"{PR_COA_0223_INTERNAL} {COMMON_FUNCTIONS}",
            ),
        ],
    },
    {
        "id": "goa-236769-prueba-exterior-rilo-01",
        "title": "Verificación de documentos comerciales en el exterior",
        "topic": "Práctica de pruebas - solicitud al exterior",
        "difficulty": 3,
        "text": (
            "En otra investigación cambiaria se requiere verificar ante una autoridad extranjera la "
            "autenticidad de facturas y la realidad de varias transacciones. El investigador prepara "
            "un correo directo al proveedor extranjero, sin el formato institucional ni los soportes, "
            "y propone suspender indefinidamente toda la investigación hasta obtener respuesta."
        ),
        "questions": [
            q(
                "¿Por conducto de qué dependencia debe tramitarse la solicitud de prueba en el exterior?",
                "De la Subdirección de Apoyo en la Lucha contra el Delito Aduanero y Fiscal, o quien haga sus veces, mediante el trámite institucional correspondiente.",
                "Directamente del investigador al proveedor extranjero, sin intervención del canal institucional.",
                "De la dependencia que recibe peticiones ciudadanas, aunque no gestione asistencia ni pruebas internacionales.",
                "Las pruebas externas no se solicitan directamente como las internas: deben tramitarse a través de la oficina o coordinación competente; el instructivo identifica a la Subdirección de Apoyo en la Lucha contra el Delito Aduanero y Fiscal.",
                f"{PR_COA_0223_INTERNAL} {IN_COT_0083}",
            ),
            q(
                "¿Qué debe corregir el investigador antes de remitir la solicitud?",
                "Diligenciar la solicitud con datos claros, exactos y completos, explicar su utilidad para la investigación y adjuntar las facturas y soportes escaneados referidos.",
                "Enviar solo el nombre del investigado y dejar que la autoridad extranjera defina qué hechos debe verificar.",
                "Eliminar las facturas y soportes para que la solicitud internacional sea más breve.",
                "IN-COT-0083 atribuye al investigador la responsabilidad por la claridad, exactitud y completitud de los datos y exige acompañar las facturas y demás soportes escaneados pertinentes.",
                IN_COT_0083,
            ),
            q(
                "Mientras llega la respuesta del exterior, ¿debe detenerse indefinidamente la investigación?",
                "No; la investigación debe continuar independientemente de que se reciba o no respuesta a la solicitud, sin desconocer los términos aplicables.",
                "Sí; toda actuación debe paralizarse sin límite hasta que responda la autoridad extranjera.",
                "Sí, y la falta de respuesta obliga a archivar automáticamente el expediente.",
                "PR-COA-0223 indica expresamente que la investigación continúa aunque todavía no se haya recibido respuesta del exterior; esta, cuando llegue, se envía a la seccional solicitante.",
                PR_COA_0223_INTERNAL,
            ),
        ],
    },
    {
        "id": "goa-236769-denfis-analisis-preliminar-01",
        "title": "Análisis preliminar de una denuncia tributaria",
        "topic": "Denuncias de fiscalización - análisis preliminar DENFIS",
        "difficulty": 3,
        "text": (
            "DENFIS asigna a una gestora una denuncia anónima que identifica a una sociedad, describe "
            "ventas presuntamente no facturadas con circunstancias de tiempo, modo y lugar y adjunta "
            "soportes. La servidora propone rechazarla por el anonimato, abrir investigación sin consultar "
            "bases institucionales y compartir los anexos con personas ajenas al trámite."
        ),
        "questions": [
            q(
                "¿Qué actuación corresponde para establecer si la denuncia tiene mérito de fiscalización?",
                "Analizar sus hechos y soportes y contrastarlos en DENFIS con bases como RUT, información exógena, Cámara de Comercio y obligaciones financieras.",
                "Rechazarla automáticamente porque el denunciante decidió no identificarse.",
                "Abrir la investigación de inmediato sin validar al denunciado ni la información aportada.",
                "La DIAN admite denuncias anónimas con hechos concretos y soportes disponibles; el rol de análisis preliminar exige consultar las bases institucionales antes de calificar la información.",
                DENFIS,
            ),
            q(
                "Antes de proponer el inicio de una acción, ¿qué conclusión debe documentar la gestora?",
                "Si los hechos son de competencia de fiscalización DIAN y si la información verificada resulta suficiente y pertinente para continuar o darle el trámite que corresponda.",
                "Que toda denuncia obliga a abrir investigación, incluso cuando trate asuntos ajenos a la DIAN.",
                "Que la identidad del denunciante es el único criterio para determinar la competencia y pertinencia.",
                "El análisis preliminar no equivale a una apertura automática: organiza y verifica la información para establecer la competencia y la pertinencia de iniciar la acción, dejando registrada la calificación en el sistema.",
                DENFIS,
            ),
            q(
                "¿Cómo deben manejarse los anexos y el resultado del análisis preliminar?",
                "Proteger la identidad y los datos suministrados, mantener la reserva de la investigación y registrar documentalmente la decisión y el trámite asignado.",
                "Publicar los anexos completos para obtener opiniones externas sobre la denuncia.",
                "Conservar la decisión únicamente en notas privadas, sin actualizar DENFIS ni el inventario documental.",
                "La información de la denuncia y la investigación está protegida; además, las funciones comunes obligan a aplicar seguridad de la información, protección de datos y adecuada organización y conservación documental.",
                f"{DENFIS} {COMMON_FUNCTIONS}",
            ),
        ],
    },
]
