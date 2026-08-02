"""Current-law customs GOA cases grounded in Law 2586 of 2026."""


def q(stem, a, b, c, rationale, article):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": (
            f"Ley 2586 de 2026, artículo {article} "
            "(Compilación Jurídica DIAN, consulta 2026-08-01)."
        ),
    }


CURATED_GAP_CASES_PHASE7 = [
    {
        "id": "goa-236769-apd-ley2586-01",
        "title": "Selección y alcance de una auditoría posterior al despacho",
        "topic": "Fiscalización aduanera - auditoría posterior al despacho",
        "difficulty": 3,
        "text": (
            "La DIAN analiza las operaciones de un importador después del levante. Los sistemas "
            "institucionales muestran diferencias que podrían corregirse voluntariamente. Parte "
            "de la revisión puede hacerse con los documentos disponibles, pero una inconsistencia "
            "requiere verificar físicamente los sistemas y archivos en el establecimiento."
        ),
        "questions": [
            q(
                "¿Cuál es la finalidad correcta de iniciar una auditoría posterior al despacho en este escenario?",
                "Prevenir nuevas infracciones y promover el cumplimiento voluntario mediante apoyo, verificación y gestión persuasiva.",
                "Imponer de inmediato una sanción sin comunicar los hallazgos al usuario.",
                "Sustituir obligatoriamente cualquier procedimiento administrativo posterior.",
                "La auditoría posterior al despacho es una actuación de control posterior orientada a prevenir nuevas infracciones y promover el cumplimiento voluntario; no constituye una sanción ni un requisito previo obligatorio.",
                "3",
            ),
            q(
                "La revisión comienza con documentos disponibles y luego exige una visita. ¿Qué tipo de auditoría corresponde?",
                "Auditoría mixta, porque combina auditoría de escritorio y visita al establecimiento.",
                "Auditoría exclusivamente de escritorio, aunque se practique la visita.",
                "Inspección judicial domiciliaria por el solo hecho de revisar archivos empresariales.",
                "La ley clasifica como mixta la auditoría que requiere tanto revisión de escritorio como visita al establecimiento.",
                "3",
            ),
            q(
                "¿Puede la dependencia afirmar que primero debe agotarse esta auditoría para abrir cualquier proceso administrativo?",
                "No. La auditoría posterior al despacho no es requisito previo para los procesos administrativos previstos en la ley.",
                "Sí. Sin auditoría previa cualquier actuación sancionatoria es nula.",
                "Sí, pero solamente cuando el importador haya aceptado todos los hallazgos.",
                "La Ley 2586 indica expresamente que la auditoría posterior al despacho no constituye requisito previo para adelantar los procedimientos administrativos.",
                "3",
            ),
        ],
    },
    {
        "id": "goa-236769-registro-prueba-ley2586-01",
        "title": "Registro, conservación de pruebas y competencia aduanera",
        "topic": "Fiscalización aduanera - registro y prueba",
        "difficulty": 3,
        "text": (
            "En una investigación aduanera existen indicios de que documentos contables y archivos "
            "pueden ser ocultados. El equipo propone registrar un establecimiento comercial y también "
            "la casa de habitación del representante legal. La orden del establecimiento sería expedida "
            "por el jefe de un grupo interno de trabajo."
        ),
        "questions": [
            q(
                "¿Qué corrección debe hacerse respecto de la autoridad que expide la orden de registro del establecimiento?",
                "Debe expedirla uno de los funcionarios legalmente competentes y la competencia es indelegable.",
                "Puede expedirla cualquier integrante del equipo investigador mediante correo electrónico.",
                "Debe expedirla exclusivamente el importador después de conocer los indicios.",
                "La ley asigna la competencia al Director de Gestión de Fiscalización, al Subdirector de Fiscalización Aduanera o al Director Seccional competente, y la declara indelegable.",
                "3",
            ),
            q(
                "¿Cómo debe procederse respecto de la casa de habitación del representante legal?",
                "Solicitar autorización judicial para practicar allí la inspección y el registro.",
                "Ingresar con la misma resolución usada para el establecimiento comercial.",
                "Descartar para siempre cualquier prueba que pudiera estar en la vivienda.",
                "El registro administrativo de establecimientos no se extiende automáticamente a la casa o lugar de habitación; para esta se requiere autorización judicial.",
                "3",
            ),
            q(
                "Ante el riesgo concreto de alteración u ocultamiento de los documentos, ¿qué puede hacer la DIAN?",
                "Adoptar la medida cautelar apropiada para conservar las pruebas, observando la cadena de custodia cuando corresponda.",
                "Destruir copias para impedir que sean discutidas por el investigado.",
                "Esperar obligatoriamente la decisión final antes de proteger cualquier evidencia.",
                "La facultad de registro permite adoptar medidas necesarias para evitar alteración, ocultamiento o destrucción de pruebas, con observancia de la cadena de custodia.",
                "3",
            ),
        ],
    },
    {
        "id": "goa-236769-precritica-persuasion-ley2586-01",
        "title": "Precrítica y gestión persuasiva de un hallazgo aduanero",
        "topic": "Fiscalización aduanera - precrítica y gestión persuasiva",
        "difficulty": 3,
        "text": (
            "Durante la precrítica de un insumo se advierte que una parte corresponde a otra entidad, "
            "otra describe un error meramente formal no sancionable y una tercera contiene indicios de "
            "inexactitud con posible sanción monetaria. La dependencia considera invitar al usuario a "
            "corregir y pagar lo correspondiente."
        ),
        "questions": [
            q(
                "¿Qué decisión corresponde frente a los hechos que no son competencia de la DIAN?",
                "Abstenerse de iniciar el proceso por esa parte y remitirla a la entidad competente.",
                "Abrir la investigación y conservarla indefinidamente aunque falte competencia.",
                "Imponer una sanción preventiva para evitar que la otra entidad conozca el caso.",
                "La falta de competencia es una causal para abstenerse de iniciar el proceso y exige remisión a la entidad competente.",
                "3",
            ),
            q(
                "¿Cómo debe tratarse el error formal no sancionable, si no hay circunstancias adicionales que ameriten investigación?",
                "Abstenerse de iniciar el proceso y dejar la decisión debidamente soportada en el acta correspondiente.",
                "Convertirlo automáticamente en una infracción gravísima.",
                "Mantener un proceso abierto hasta que el usuario reconozca una sanción inexistente.",
                "La ley prevé abstención cuando la conducta es un error formal no sancionable, salvo que existan circunstancias que ameriten abrir investigación, y exige soportar la decisión en acta.",
                "3",
            ),
            q(
                "La DIAN envía una invitación persuasiva por la posible inexactitud. ¿Qué efecto tiene que el usuario no responda?",
                "La falta de respuesta no genera por sí misma sanción; vencido el término, la autoridad puede continuar con el procedimiento que corresponda.",
                "Produce aceptación automática de todos los hechos y una sanción adicional.",
                "Obliga a cerrar definitivamente cualquier actuación relacionada con la operación.",
                "La gestión persuasiva permite corregir o allanarse voluntariamente; la no respuesta no ocasiona sanción, sin impedir que después se inicie el procedimiento aplicable.",
                "5",
            ),
        ],
    },
]
