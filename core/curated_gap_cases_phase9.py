"""Tax audit and evidence GOA cases grounded in the Colombian Tax Statute."""


def q(stem, a, b, c, rationale, source):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": source,
    }


ET = "Estatuto Tributario, artículo {article} (Compilación Jurídica DIAN, consulta 2026-08-01)."


CURATED_GAP_CASES_PHASE9 = [
    {
        "id": "goa-236769-tributario-facultades-01",
        "title": "Verificación de una declaración mediante información cruzada",
        "topic": "Fiscalización tributaria - facultades y alcance",
        "difficulty": 3,
        "text": (
            "Al comparar una declaración de renta con información de terceros, el auditor encuentra "
            "ingresos y costos que no coinciden. Propone pedir soportes al contribuyente y a sus clientes, "
            "examinar parcialmente libros y comprobantes y trasladar una prueba recaudada en otro "
            "proceso que versa sobre las mismas operaciones."
        ),
        "questions": [
            q(
                "¿Está dentro de las facultades de fiscalización solicitar documentos y examinar libros relacionados con las diferencias?",
                "Sí, porque la DIAN puede verificar declaraciones, requerir informes y documentos y examinar libros y comprobantes pertinentes.",
                "No, porque solo puede revisar los datos escritos en la declaración sin acudir a terceros.",
                "No, salvo que primero exista una liquidación oficial ejecutoriada.",
                "Las amplias facultades de fiscalización permiten verificar la exactitud de declaraciones, requerir información y examinar documentos necesarios para determinar correctamente los impuestos.",
                ET.format(article="684"),
            ),
            q(
                "¿Qué condición es decisiva para trasladar y valorar la prueba obtenida en el otro proceso?",
                "Que verse sobre las mismas circunstancias fácticas y se incorpore respetando la posibilidad de contradicción.",
                "Que provenga de cualquier expediente, aunque trate hechos y periodos diferentes.",
                "Que favorezca necesariamente la hipótesis inicial del auditor.",
                "La doctrina DIAN admite trasladar pruebas recaudadas incluso respecto de terceros cuando versan sobre las mismas circunstancias; su valoración debe respetar el debido proceso.",
                "DIAN, Concepto 002097 de 2024; Estatuto Tributario, artículos 684 y 742.",
            ),
            q(
                "Si los soportes permiten una explicación coherente de parte de las diferencias, ¿cómo debe actuar el auditor?",
                "Analizar integralmente la explicación y ajustar la hipótesis a los hechos efectivamente probados.",
                "Mantener todas las glosas porque la selección inicial del caso es inmodificable.",
                "Excluir los soportes por haber sido entregados después de detectar las diferencias.",
                "La fiscalización busca la determinación correcta y debe facilitar la aclaración de dudas u omisiones, no confirmar a toda costa una hipótesis previa.",
                ET.format(article="683 y 684"),
            ),
        ],
    },
    {
        "id": "goa-236769-tributario-valoracion-prueba-01",
        "title": "Valoración de hechos y vacíos probatorios",
        "topic": "Régimen probatorio tributario - valoración y suficiencia",
        "difficulty": 3,
        "text": (
            "En un expediente, una glosa se apoya principalmente en la opinión de un tercero. El "
            "contribuyente aporta contratos, facturas y comprobantes oportunamente. Algunos documentos "
            "presentan inconsistencias menores, pero el equipo no practica las verificaciones disponibles "
            "y propone decidir únicamente a partir de la sospecha inicial."
        ),
        "questions": [
            q(
                "¿Cuál es la exigencia principal antes de adoptar la decisión administrativa?",
                "Fundarla en hechos demostrados dentro del expediente mediante medios de prueba legalmente admisibles.",
                "Fundarla en la intuición del auditor aunque contradiga los documentos recaudados.",
                "Copiar la opinión del tercero sin valorar las demás pruebas.",
                "La determinación de tributos y la imposición de sanciones deben apoyarse en hechos probados en el expediente.",
                ET.format(article="742"),
            ),
            q(
                "¿La opinión del tercero obliga por sí sola a la Administración a mantener la glosa?",
                "No; debe contrastarse con los hechos y las demás pruebas y no sustituye la valoración administrativa.",
                "Sí; cualquier opinión de un tercero prevalece sobre los soportes del contribuyente.",
                "Sí, pero únicamente cuando la opinión no identifica su fuente.",
                "Las opiniones de terceros no obligan a la Administración y la decisión debe resultar de la valoración del conjunto probatorio.",
                ET.format(article="687 y 742"),
            ),
            q(
                "Si después de agotar razonablemente la actividad probatoria persiste una duda causada por un vacío de prueba, ¿qué regla debe considerarse?",
                "Resolverla a favor del contribuyente cuando este no estaba legalmente obligado a demostrar el hecho omitido.",
                "Convertir toda duda en una presunción automática contra el contribuyente.",
                "Imponer la glosa y buscar la prueba únicamente después de la decisión.",
                "El Estatuto prevé que las dudas originadas en vacíos probatorios se resuelven a favor del contribuyente cuando no existe deber legal de probar el hecho correspondiente.",
                ET.format(article="745"),
            ),
        ],
    },
    {
        "id": "goa-236769-tributario-inspeccion-01",
        "title": "Delimitación y práctica de una inspección tributaria",
        "topic": "Fiscalización tributaria - inspecciones",
        "difficulty": 3,
        "text": (
            "Para comprobar costos declarados, la dependencia proyecta una inspección tributaria. El "
            "auto se limita a ordenar una revisión general sin identificar los hechos materia de prueba "
            "ni los funcionarios comisionados. Durante la diligencia se considera revisar soportes y "
            "libros relacionados con las operaciones investigadas."
        ),
        "questions": [
            q(
                "¿Qué debe corregirse en el auto que decreta la inspección tributaria?",
                "Señalar clara y específicamente los hechos materia de prueba y los funcionarios comisionados.",
                "Eliminar toda referencia al objeto para impedir que el contribuyente prepare su defensa.",
                "Reemplazar el auto por una llamada telefónica sin constancia escrita.",
                "La inspección debe decretarse mediante auto que delimite los hechos objeto de prueba e identifique a los funcionarios autorizados.",
                "Estatuto Tributario, artículo 779; DIAN, Concepto 000101 de 2025.",
            ),
            q(
                "¿Puede la inspección tributaria incluir la revisión de libros y documentos relacionados con los costos investigados?",
                "Sí, como parte de los medios legalmente autorizados para verificar los hechos delimitados en la inspección.",
                "No, porque en una inspección tributaria está prohibido observar cualquier documento contable.",
                "Sí, pero solamente para investigar operaciones ajenas a los hechos indicados en el auto.",
                "La inspección tributaria permite utilizar medios de prueba autorizados, incluida la verificación de libros y soportes pertinentes, dentro del objeto decretado.",
                "Estatuto Tributario, artículos 779 y 684; Consejo de Estado, Sección Cuarta, expediente 20661 de 2016.",
            ),
            q(
                "¿Cómo debe cerrarse documentalmente la diligencia practicada?",
                "Con un acta que recoja los hechos, pruebas y resultados relevantes de la inspección.",
                "Sin registro, porque el auto inicial reemplaza cualquier constancia posterior.",
                "Con una sanción automática, aunque la prueba no demuestre inexactitud.",
                "La práctica de la inspección debe quedar documentada para que sus resultados puedan incorporarse, valorarse y controvertirse dentro del expediente.",
                ET.format(article="779"),
            ),
        ],
    },
]
