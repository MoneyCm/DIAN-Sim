"""Final four source-grounded GOA cases for the 14-case gap matrix."""

def q(stem, a, b, c, rationale, source):
    return {"stem": stem, "options": {"A": a, "B": b, "C": c}, "correct_key": "A", "rationale": rationale, "source_ref": source}


CURATED_GAP_CASES_PHASE5 = [
    {"id": "goa-236769-internacional-plena-01", "title": "Margen pactado con una vinculada extranjera", "topic": "Fiscalización internacional - plena competencia", "difficulty": 3,
     "text": "Una sociedad colombiana vende el mismo servicio a su matriz extranjera con margen del 2% y a terceros independientes comparables con margen del 15%. No documenta diferencias de funciones, activos o riesgos que expliquen la brecha.",
     "questions": [
        q("¿Qué aspecto debe comprobar prioritariamente el auditor?", "Si la operación vinculada cumple el principio de plena competencia.", "Si toda venta al exterior está prohibida.", "Si la matriz usa la misma moneda.", "Las operaciones con vinculados deben determinarse considerando condiciones entre independientes.", "Estatuto Tributario, artículos 260-1 y 260-2 (Compilación Jurídica DIAN)."),
        q("¿Qué dato ofrece el comparable más directo en este caso?", "El margen del 15% obtenido con terceros independientes comparables.", "La residencia extranjera de la matriz por sí sola.", "El nombre comercial del servicio.", "Los comparables internos deben considerarse prioritariamente cuando existen.", "Estatuto Tributario, artículo 260-5, parágrafo."),
        q("¿Qué información podría explicar legítimamente la diferencia de márgenes?", "Diferencias demostradas en funciones, activos y riesgos.", "La sola decisión del grupo de usar 2%.", "La ausencia de una importación física.", "El análisis debe atender las condiciones económicas efectivas de operaciones comparables.", "Estatuto Tributario, régimen de precios de transferencia, artículos 260-1 a 260-5."),
     ]},
    {"id": "goa-236769-internacional-umbral-01", "title": "Umbral de documentación comprobatoria", "topic": "Fiscalización internacional - documentación", "difficulty": 3,
     "text": "Una contribuyente de renta tiene patrimonio bruto de 80.000 UVT e ingresos brutos de 70.000 UVT. Durante el año celebra operaciones con una vinculada del exterior, pero sostiene que no prepara documentación porque su patrimonio no llega a 100.000 UVT.",
     "questions": [
        q("¿Es correcta la conclusión de la contribuyente?", "No, porque sus ingresos superan el umbral alternativo de 61.000 UVT.", "Sí, porque solo importa el patrimonio.", "Sí, porque ninguna operación exterior se documenta.", "La obligación surge por patrimonio igual o superior a 100.000 UVT o ingresos iguales o superiores a 61.000 UVT.", "Estatuto Tributario, artículo 260-5."),
        q("¿Qué dato del caso activa la obligación pese al patrimonio inferior?", "Los ingresos brutos de 70.000 UVT.", "El patrimonio de 80.000 UVT.", "La mera denominación de contribuyente de renta.", "El umbral de ingresos opera de manera alternativa al de patrimonio.", "Estatuto Tributario, artículo 260-5."),
        q("¿Qué debe contener la documentación aplicable a las operaciones descritas?", "Informe maestro e informe local en los términos legales.", "Solo una factura comercial sin análisis.", "Únicamente un ROS enviado a la UIAF.", "El artículo 260-5 exige informe maestro e informe local para los obligados.", "Estatuto Tributario, artículo 260-5."),
     ]},
    {"id": "goa-236769-aduanas-analisis-integral-01", "title": "Descripción que identifica una mercancía diferente", "topic": "Fiscalización aduanera - análisis integral", "difficulty": 3,
     "text": "En control posterior, la declaración describe repuestos de baja capacidad. La factura, ficha técnica y seriales corresponden a equipos completos de mayor capacidad; la diferencia no es un error menor y permite identificar mercancía distinta de la declarada.",
     "questions": [
        q("¿Qué comparación debe efectuar la autoridad?", "Declaración aduanera frente a factura, ficha técnica y seriales.", "Factura frente a publicidad general.", "Seriales frente al domicilio del importador.", "El análisis integral posterior compara la declaración con sus documentos soporte.", "Decreto 1165 de 2019, definición de análisis integral y artículo 581."),
        q("¿Qué consecuencia analítica tiene la descripción del caso?", "Puede establecer que la mercancía controlada es diferente de la declarada.", "Debe tratarse siempre como error sin relevancia.", "Convierte el control en previo.", "Los errores u omisiones de descripción se analizan para determinar si la mercancía es diferente.", "Decreto 1165 de 2019, definición de análisis integral."),
        q("¿Por qué puede profundizarse la investigación después del levante?", "Porque el control posterior permite comprobar exactitud y requisitos tras la nacionalización.", "Porque el levante elimina toda competencia de la DIAN.", "Porque solo el importador puede revisar la declaración.", "El artículo 581 habilita comprobaciones, estudios e investigaciones posteriores.", "Decreto 1165 de 2019, artículo 581."),
     ]},
    {"id": "goa-236769-cambiario-canalizacion-ficticia-01", "title": "Canalización sin operación de comercio exterior", "topic": "Régimen cambiario - canalización indebida", "difficulty": 3,
     "text": "Una sociedad canaliza USD 40.000 como pago de una importación. La DIAN verifica que no existe proveedor, factura, declaración aduanera ni mercancía y que el dinero fue enviado a una cuenta de un tercero sin relación comercial.",
     "questions": [
        q("¿Qué conducta refleja el conjunto de hallazgos?", "Canalizar como importación un monto que no deriva de esa operación.", "Presentar tardíamente una declaración real.", "Canalizar una diferencia documental justificada.", "El numeral 7 sanciona canalizar montos que no se derivan de importaciones, exportaciones o su financiación.", "Decreto-Ley 2245 de 2011, artículo 3 numeral 7."),
        q("¿Cuál es la base de la multa prevista para la conducta descrita?", "El 100% de los USD 40.000 canalizados, convertido conforme corresponda.", "Solo la diferencia entre dos facturas inexistentes.", "25 UVT sin considerar la operación.", "El numeral 7 fija el 100% del valor indebidamente canalizado.", "Decreto-Ley 2245 de 2011, artículo 3 numeral 7."),
        q("¿Qué evidencia del caso diferencia esta conducta de una simple diferencia justificada?", "La inexistencia total de proveedor, factura, declaración y mercancía.", "El uso de dólares estadounidenses.", "El envío mediante una entidad financiera.", "Los documentos y la realidad económica muestran que el monto no proviene de una importación.", "Decreto-Ley 2245 de 2011, artículo 3 numerales 7 y 8."),
     ]},
]
