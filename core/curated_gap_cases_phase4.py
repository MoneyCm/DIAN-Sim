"""Evidence, customs control and contraband GOA cases for OPEC 236769."""

def q(stem, a, b, c, rationale, source):
    return {"stem": stem, "options": {"A": a, "B": b, "C": c}, "correct_key": "A", "rationale": rationale, "source_ref": source}


CURATED_GAP_CASES_PHASE4 = [
    {"id": "goa-236769-pruebas-expediente-01", "title": "Vacío probatorio en determinación tributaria", "topic": "Práctica y valoración de pruebas", "difficulty": 3,
     "text": "Un auditor propone desconocer un costo basándose únicamente en una alerta interna. La factura, el contrato y el pago obran en el expediente y no fueron controvertidos. La alerta no contiene documentos que demuestren que la operación sea inexistente.",
     "questions": [
        q("¿Qué debe hacer el auditor antes de proponer la decisión?", "Practicar y valorar pruebas que demuestren los hechos en el expediente.", "Desconocer el costo solo por la alerta.", "Excluir los soportes por provenir del contribuyente.", "Las decisiones deben fundarse en hechos probados en el expediente.", "Estatuto Tributario, artículo 742 (Compilación Jurídica DIAN)."),
        q("¿Qué documentos del caso deben ser valorados por su conexión con la operación?", "La factura, el contrato y el comprobante de pago.", "Únicamente la alerta interna.", "Solo el registro mercantil de la sociedad.", "La idoneidad depende de la exigencia legal, conexión con el hecho y sana crítica.", "Estatuto Tributario, artículos 742 y 743 (Compilación Jurídica DIAN)."),
        q("Si después de agotar la actividad probatoria persiste un vacío no atribuible al contribuyente, ¿cómo se resuelve la duda?", "A favor del contribuyente.", "Siempre a favor de la Administración.", "Mediante una sanción provisional.", "Las dudas provenientes de vacíos probatorios se resuelven a favor del contribuyente.", "Estatuto Tributario, artículo 745 (Compilación Jurídica DIAN)."),
     ]},
    {"id": "goa-236769-pruebas-inspeccion-01", "title": "Delimitación de una inspección tributaria", "topic": "Práctica y valoración de pruebas", "difficulty": 3,
     "text": "La DIAN proyecta inspeccionar a una sociedad por diferencias entre ingresos bancarios y declarados. El borrador del auto dice solamente 'verificar todas las obligaciones', sin identificar periodos, transacciones ni hechos específicos.",
     "questions": [
        q("¿Qué defecto debe corregirse antes de decretar la inspección?", "Precisar los hechos materia de prueba.", "Eliminar toda referencia a las diferencias bancarias.", "Imponer primero una sanción.", "El auto debe delimitar clara y específicamente los hechos objeto de prueba.", "Estatuto Tributario, artículo 779 y Concepto DIAN 101 de 2025."),
        q("¿Qué formulación responde mejor al hallazgo del caso?", "Verificar las diferencias de ingresos del periodo y transacciones identificadas.", "Revisar cualquier asunto presente o futuro sin límite.", "Examinar solo la existencia jurídica de la sociedad.", "La delimitación permite conocer el objeto de la inspección y ejercer defensa.", "Concepto DIAN 101 de 2025; artículos 742, 743 y 779 E.T."),
        q("¿Qué garantía protege esa delimitación concreta?", "El debido proceso y el derecho de defensa del contribuyente.", "La reserva absoluta frente al propio contribuyente.", "La imposición automática de la liquidación.", "La identificación precisa permite preparar los medios de defensa.", "Concepto DIAN 101 de 2025."),
     ]},
    {"id": "goa-236769-aduanas-facultades-01", "title": "Verificación posterior de documentos aduaneros", "topic": "Fiscalización aduanera - facultades", "difficulty": 3,
     "text": "Después del levante, la DIAN detecta que la descripción de una mercancía en la declaración no coincide con la factura ni con el catálogo técnico. La diferencia podría implicar menor tributo y el importador conserva los soportes.",
     "questions": [
        q("¿Qué facultad se ajusta directamente al hallazgo?", "Verificar la exactitud de la declaración y sus documentos soporte.", "Modificar el arancel mediante circular interna.", "Declarar responsabilidad penal del importador.", "La DIAN puede verificar exactitud para establecer menor tributo o incumplimiento.", "Decreto 1165 de 2019, artículo 591 numeral 3."),
        q("¿Por qué la actuación se ubica en control posterior?", "Porque se realiza después del levante sobre declaración y soportes.", "Porque antecede a la llegada de la mercancía.", "Porque ocurre durante la inspección previa.", "El control posterior opera tras nacionalización o finalización del régimen.", "Decreto 1165 de 2019, artículo 581."),
        q("¿Qué comparación es central para determinar la inexactitud descrita?", "Declaración frente a factura y catálogo técnico.", "Catálogo frente a publicidad de competidores.", "Factura frente al domicilio del importador.", "El caso exige comprobar la exactitud de declaración y documentos soporte.", "Decreto 1165 de 2019, artículos 581 y 591."),
     ]},
    {"id": "goa-236769-contrabando-denuncia-01", "title": "Hallazgo aduanero con posible relevancia penal", "topic": "Contrabando y coordinación institucional", "difficulty": 3,
     "text": "En un control, la DIAN encuentra combustible extranjero oculto en tanques adicionales de un vehículo. La cantidad alcanza el supuesto penal aplicable. Hay elementos para la actuación aduanera, pero la responsabilidad penal del conductor no ha sido definida.",
     "questions": [
        q("¿Qué debe hacer la autoridad aduanera frente al posible delito?", "Presentar la denuncia ante la autoridad penal competente.", "Declarar penalmente responsable al conductor.", "Omitir el traslado hasta terminar todos los procesos administrativos.", "La DIAN denuncia; la responsabilidad penal se define por la autoridad competente.", "Decreto 1165 de 2019, artículo 601; Concepto DIAN 32143 de 2019."),
        q("¿Qué límite competencial debe respetar el funcionario?", "No decidir la responsabilidad penal del conductor.", "No adelantar ninguna actuación aduanera.", "No conservar pruebas del hallazgo.", "La DIAN carece de competencia para definir responsabilidad por el delito.", "Concepto DIAN 32143 de 2019."),
        q("¿Cuál dato del caso activa la necesidad de coordinación penal?", "Que la cantidad alcanza el supuesto penal y el combustible estaba oculto.", "Que el vehículo tiene propietario registrado.", "Que el control fue realizado por la DIAN.", "La adecuación al supuesto penal exige denuncia a la autoridad competente.", "Concepto DIAN 32143 de 2019; artículo 601 Decreto 1165 de 2019."),
     ]},
]
