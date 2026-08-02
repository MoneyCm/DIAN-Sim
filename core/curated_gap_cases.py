"""Human-authored, source-grounded GOA cases for OPEC 236769."""

CURATED_GAP_CASES = [
    {
        "id": "goa-236769-aduanas-control-posterior-01",
        "title": "Diferencia entre la declaración y los soportes comerciales",
        "topic": "Fiscalización aduanera - control posterior",
        "difficulty": 3,
        "text": (
            "Después de la nacionalización de una máquina industrial, una gestora de fiscalización "
            "compara la declaración de importación, que registra USD 250.000, con la factura definitiva "
            "y el comprobante bancario por USD 310.000. El importador no aportó una nota crédito ni otro "
            "documento que explique la diferencia. La revisión se realiza seis meses después del levante "
            "y todavía no se ha expedido un acto de determinación ni una sanción."
        ),
        "questions": [
            {
                "stem": "Con la etapa y los documentos descritos, ¿cómo debe encuadrar inicialmente la gestora su actuación?",
                "options": {
                    "A": "Como control posterior, contrastando la declaración con los documentos comerciales para comprobar su exactitud.",
                    "B": "Como control previo, porque la factura definitiva antecede a cualquier actuación sancionatoria.",
                    "C": "Como control simultáneo, porque el pago bancario forma parte de la operación de importación.",
                },
                "correct_key": "A",
                "rationale": "El control ocurre después de la nacionalización y recae sobre la declaración y sus soportes; corresponde al control posterior del artículo 581 del Decreto 1165 de 2019.",
                "source_ref": "Decreto 1165 de 2019, artículo 581 (Compilación Jurídica DIAN).",
            },
            {
                "stem": "¿Cuál hallazgo del caso sustenta directamente que la gestora profundice la comprobación de la exactitud declarada?",
                "options": {
                    "A": "La diferencia de USD 60.000 entre el valor declarado y los documentos de pago, sin soporte que la explique.",
                    "B": "Que la maquinaria industrial fue nacionalizada seis meses antes de la revisión.",
                    "C": "Que todavía no se ha expedido un acto administrativo sancionatorio.",
                },
                "correct_key": "A",
                "rationale": "La discrepancia no justificada entre declaración, factura y pago es el dato concreto que compromete la exactitud objeto de comprobación en el control posterior.",
                "source_ref": "Decreto 1165 de 2019, artículo 581 (Compilación Jurídica DIAN).",
            },
            {
                "stem": "Si la diferencia constituye un indicio de inexactitud con posible sanción monetaria, ¿qué actuación prevista expresamente puede adelantar la DIAN antes de continuar el proceso?",
                "options": {
                    "A": "Emplazar al usuario mediante gestión persuasiva para que actúe dentro del mes siguiente en los términos legales.",
                    "B": "Ordenar automáticamente el decomiso definitivo porque el pago supera el valor declarado.",
                    "C": "Archivar la revisión porque ya se produjo el levante de la mercancía.",
                },
                "correct_key": "A",
                "rationale": "Ante indicios de inexactitud o infracción monetaria, el artículo 593 permite la gestión persuasiva y el emplazamiento por el término allí señalado.",
                "source_ref": "Decreto 1165 de 2019, artículo 593 (Compilación Jurídica DIAN).",
            },
        ],
    },
    {
        "id": "goa-236769-cambiario-declaraciones-01",
        "title": "Declaraciones de cambio y soportes faltantes",
        "topic": "Régimen cambiario - declaración de cambio",
        "difficulty": 3,
        "text": (
            "En una investigación sobre pagos de importaciones, la DIAN identifica cuatro operaciones "
            "independientes: dos declaraciones de cambio no fueron presentadas oportunamente, una fue "
            "presentada con datos equivocados y en otra el investigado no conservó los documentos que "
            "acreditaban el destino de las divisas. No se detectaron otras infracciones cambiarias."
        ),
        "questions": [
            {
                "stem": "¿Cuál tratamiento refleja conjuntamente las cuatro conductas encontradas?",
                "options": {
                    "A": "Cada una encaja en las conductas relativas a declaración de cambio previstas en el numeral 1 del artículo 3.",
                    "B": "Solo las dos declaraciones extemporáneas son infracciones; los demás defectos se corrigen sin consecuencia.",
                    "C": "Todas constituyen transferencias internacionales no autorizadas del numeral 24.",
                },
                "correct_key": "A",
                "rationale": "El numeral 1 comprende presentación inoportuna, datos equivocados y falta de conservación o exhibición de soportes.",
                "source_ref": "Decreto-Ley 2245 de 2011, artículo 3, numeral 1 (Compilación Jurídica DIAN).",
            },
            {
                "stem": "Con los cuatro incumplimientos independientes descritos, ¿qué multa resulta antes de aplicar el límite por investigación?",
                "options": {"A": "25 UVT.", "B": "100 UVT.", "C": "1.000 UVT."},
                "correct_key": "B",
                "rationale": "La norma fija 25 UVT por declaración; cuatro conductas asociadas a cuatro declaraciones producen 100 UVT, cifra inferior al máximo de 1.000 UVT.",
                "source_ref": "Decreto-Ley 2245 de 2011, artículo 3, numeral 1 (Compilación Jurídica DIAN).",
            },
            {
                "stem": "¿Qué dato adicional cambiaría el cálculo al activar el límite máximo previsto para esta clase de conductas?",
                "options": {
                    "A": "Que la investigación comprendiera más de cuarenta declaraciones sancionables bajo el mismo numeral.",
                    "B": "Que una de las operaciones correspondiera a una importación de maquinaria.",
                    "C": "Que el investigado entregara voluntariamente sus registros contables.",
                },
                "correct_key": "A",
                "rationale": "A 25 UVT por declaración, más de cuarenta superarían 1.000 UVT; opera entonces el máximo de 1.000 UVT por investigación.",
                "source_ref": "Decreto-Ley 2245 de 2011, artículo 3, numeral 1 (Compilación Jurídica DIAN).",
            },
        ],
    },
    {
        "id": "goa-236769-cambiario-canalizacion-01",
        "title": "Diferencia canalizada con soporte contractual",
        "topic": "Régimen cambiario - canalización",
        "difficulty": 3,
        "text": (
            "Un importador canalizó USD 118.000, aunque la declaración aduanera indicaba USD 100.000. "
            "Al ser requerido, aporta contrato, factura definitiva y comprobantes que muestran que los "
            "USD 18.000 adicionales corresponden a una obligación real asociada con la operación. El "
            "análisis integral confirma la trazabilidad y no encuentra pagos ficticios."
        ),
        "questions": [
            {
                "stem": "¿Qué elemento del caso es decisivo para valorar la diferencia canalizada?",
                "options": {
                    "A": "La prueba documental de que los USD 18.000 corresponden al monto real de la obligación.",
                    "B": "La sola existencia de una diferencia frente a la declaración aduanera.",
                    "C": "Que el importador haya usado dólares estadounidenses como moneda de pago.",
                },
                "correct_key": "A",
                "rationale": "El numeral 8 contempla que no hay infracción cuando se prueba que el valor canalizado corresponde a la obligación real o existe causa justificada documentada.",
                "source_ref": "Decreto-Ley 2245 de 2011, artículo 3, numeral 8 (Compilación Jurídica DIAN).",
            },
            {
                "stem": "Con la evidencia confirmada por el análisis integral, ¿cuál conclusión corresponde?",
                "options": {
                    "A": "La diferencia puede quedar amparada por la excepción y no configurar la infracción del numeral 8.",
                    "B": "Debe imponerse siempre una multa del 100% de USD 118.000.",
                    "C": "Debe desconocerse la documentación porque fue entregada después de la canalización.",
                },
                "correct_key": "A",
                "rationale": "La norma exceptúa la diferencia probada y justificada; el caso aporta precisamente esa evidencia.",
                "source_ref": "Decreto-Ley 2245 de 2011, artículo 3, numeral 8 (Compilación Jurídica DIAN).",
            },
            {
                "stem": "Si el importador no hubiera aportado ningún soporte y la diferencia permaneciera injustificada, ¿sobre qué base se calcularía la multa del numeral 8?",
                "options": {"A": "Sobre USD 18.000.", "B": "Sobre USD 100.000.", "C": "Sobre USD 118.000."},
                "correct_key": "A",
                "rationale": "El numeral 8 establece el 100% de la diferencia entre el valor canalizado y el consignado en los documentos aduaneros.",
                "source_ref": "Decreto-Ley 2245 de 2011, artículo 3, numeral 8 (Compilación Jurídica DIAN).",
            },
        ],
    },
]

