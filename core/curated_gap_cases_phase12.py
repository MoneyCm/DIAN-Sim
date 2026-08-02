"""Cross-cutting administrative-procedure GOA cases for OPEC 236769."""


def q(stem, a, b, c, rationale, articles):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": (
            f"Ley 1437 de 2011, artículo(s) {articles} "
            "(Gestor Normativo de Función Pública, consulta 2026-08-01)."
        ),
    }


CURATED_GAP_CASES_PHASE12 = [
    {
        "id": "goa-236769-cpaca-competencia-remision-01",
        "title": "Petición recibida por una dependencia sin competencia",
        "topic": "Procedimiento administrativo - competencia y remisión",
        "difficulty": 3,
        "text": (
            "Un ciudadano presenta por escrito ante una dependencia de la DIAN una solicitud que debe "
            "resolver otra autoridad. El servidor identifica con claridad la entidad competente, pero "
            "considera conservar la petición hasta responder que la DIAN carece de competencia."
        ),
        "questions": [
            q(
                "¿Qué actuación inicial corresponde frente a la petición escrita?",
                "Informar al interesado dentro de cinco días y remitir la petición al competente dentro del mismo término.",
                "Archivarla sin comunicación porque la DIAN no resolverá el fondo.",
                "Decidir el asunto aunque la competencia corresponda a otra autoridad.",
                "La autoridad sin competencia debe informar y remitir oportunamente, enviando al peticionario copia del oficio remisorio.",
                "21",
            ),
            q(
                "¿Desde cuándo se cuentan los términos para que la autoridad competente decida o responda?",
                "Desde el día siguiente a la recepción de la petición por la autoridad competente.",
                "Desde la fecha en que el ciudadano redactó la petición, aunque no la hubiera presentado.",
                "Desde que la primera dependencia decida archivar su copia del oficio.",
                "El término para responder empieza el día siguiente a aquel en que la petición es recibida por la autoridad competente.",
                "21",
            ),
            q(
                "Si después de verificar no existiera una autoridad competente identificable, ¿qué debe hacer el servidor?",
                "Comunicar esa circunstancia al peticionario dentro del término aplicable.",
                "Inventar una autoridad destinataria para cerrar el trámite interno.",
                "Guardar silencio porque no puede remitir físicamente el documento.",
                "Cuando no existe funcionario competente al cual remitir, la norma exige informarlo al interesado.",
                "21",
            ),
        ],
    },
    {
        "id": "goa-236769-cpaca-impedimento-01",
        "title": "Interés particular en una actuación administrativa",
        "topic": "Procedimiento administrativo - impedimentos y recusaciones",
        "difficulty": 3,
        "text": (
            "A un servidor le asignan el análisis de una actuación cuyo resultado puede beneficiar "
            "directamente a una sociedad de la que su cónyuge es socia. Aunque cree poder actuar con "
            "objetividad, reconoce el vínculo al revisar el expediente y todavía no ha practicado pruebas."
        ),
        "questions": [
            q(
                "¿Cuál es la conducta jurídicamente adecuada al conocer el vínculo?",
                "Declararse impedido porque existe un interés particular y directo relacionado con el asunto.",
                "Continuar y revelar el vínculo únicamente después de adoptar la decisión final.",
                "Preguntar a la sociedad beneficiaria si autoriza que siga conociendo el expediente.",
                "El conflicto entre interés general e interés particular directo del servidor o de los sujetos señalados por la ley exige manifestar el impedimento.",
                "11",
            ),
            q(
                "¿Cómo debe tramitar el servidor su impedimento?",
                "Enviar la actuación, dentro de los tres días siguientes a su conocimiento, con escrito motivado al superior competente.",
                "Abandonar el expediente sin constancia ni entrega formal.",
                "Resolver primero las pruebas y remitir solamente si el resultado favorece a la sociedad.",
                "El impedimento se remite con motivación dentro de tres días al superior o a la autoridad prevista por la ley cuando aquel no existe.",
                "12",
            ),
            q(
                "Mientras se decide de fondo el impedimento, ¿puede continuar practicando pruebas en el asunto?",
                "No; debe abstenerse de seguir actuando mientras la actuación permanece suspendida por el trámite del impedimento.",
                "Sí; el impedimento solo afecta la firma de la decisión definitiva.",
                "Sí, si evita dejar registro de las diligencias practicadas.",
                "Manifestado el impedimento, la actuación se suspende hasta que la autoridad competente lo resuelva.",
                "12",
            ),
        ],
    },
    {
        "id": "goa-236769-cpaca-prueba-decision-01",
        "title": "Contradicción probatoria y contenido de la decisión",
        "topic": "Procedimiento administrativo - prueba y decisión",
        "difficulty": 3,
        "text": (
            "Durante una actuación administrativa, el interesado solicita oportunamente una prueba "
            "pertinente y un tercero reconocido aporta un informe antes de la decisión. La dependencia "
            "proyecta negar la prueba sin motivar, usar el informe sin permitir contradicción y resolver "
            "solo una de las peticiones formuladas."
        ),
        "questions": [
            q(
                "¿Hasta qué momento pueden aportarse, pedirse y practicarse pruebas dentro de la actuación general?",
                "Hasta antes de que se profiera la decisión de fondo, de oficio o a petición del interesado.",
                "Únicamente durante el día de presentación de la solicitud inicial.",
                "Solo después de proferida y notificada la decisión definitiva.",
                "El CPACA admite actividad probatoria durante la actuación y hasta antes de la decisión de fondo, sin requisitos especiales en la regla general.",
                "40",
            ),
            q(
                "¿Puede la autoridad basarse en el informe del tercero sin dar oportunidad de controvertirlo?",
                "No; el interesado debe poder controvertir las pruebas aportadas o practicadas antes de la decisión de fondo.",
                "Sí; la contradicción solo existe en procesos judiciales.",
                "Sí, siempre que el informe respalde la hipótesis de la dependencia.",
                "La garantía de contradicción probatoria debe hacerse efectiva antes de dictar la decisión de fondo.",
                "40",
            ),
            q(
                "¿Qué alcance debe tener la decisión final una vez escuchados los interesados y valoradas las pruebas?",
                "Ser motivada y resolver todas las peticiones planteadas oportunamente por el peticionario y los terceros reconocidos.",
                "Resolver solo la petición más fácil y guardar silencio frente a las demás.",
                "Limitarse a enumerar pruebas sin explicar la decisión adoptada.",
                "La decisión debe apoyarse en pruebas e informes, estar motivada y pronunciarse sobre todas las peticiones oportunas.",
                "42",
            ),
        ],
    },
]
