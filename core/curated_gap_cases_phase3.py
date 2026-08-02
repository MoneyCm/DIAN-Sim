"""Third human-authored GOA batch for OPEC 236769."""

CURATED_GAP_CASES_PHASE3 = [{
    "id": "goa-236769-denuncias-precritica-01", "title": "Precrítica de una denuncia anónima", "topic": "Precrítica y denuncias", "difficulty": 2,
    "text": "La DIAN recibe una denuncia anónima contra Comercial Delta S.A.S. Incluye NIT, dirección, fechas, lugares, ventas no facturadas y comprobantes. Dos días después llega otra comunicación con exactamente los mismos hechos y anexos.",
    "questions": [
        {"stem": "¿Qué decisión inicial corresponde respecto de la primera denuncia?", "options": {"A": "Analizarla porque admite anonimato y contiene datos concretos y pruebas.", "B": "Rechazarla por no identificar al denunciante.", "C": "Tramitarla solo como petición informativa."}, "correct_key": "A", "rationale": "El sistema admite denuncias anónimas y solicita datos del denunciado, hechos concretos y pruebas disponibles.", "source_ref": "Sistema de Denuncias de Fiscalización DIAN, instrucciones oficiales."},
        {"stem": "¿Cómo debe valorarse la segunda comunicación durante la precrítica?", "options": {"A": "Como repetición sin mayor efecto que la inicial.", "B": "Como obligación de abrir otra investigación idéntica.", "C": "Como sustitución automática de la primera."}, "correct_key": "A", "rationale": "Repetir la misma denuncia con iguales hechos no genera mayor efecto que la inicial.", "source_ref": "Sistema de Denuncias de Fiscalización DIAN, instrucciones oficiales."},
        {"stem": "¿Qué dato permite clasificar el insumo como denuncia tributaria?", "options": {"A": "Las ventas presuntamente no facturadas.", "B": "La dirección conocida.", "C": "Los dos días entre comunicaciones."}, "correct_key": "A", "rationale": "La omisión de facturación constituye el posible incumplimiento tributario material.", "source_ref": "DIAN, guía pública de denuncias TAC."},
    ],
}, {
    "id": "goa-236769-laft-ros-01", "title": "Señales de alerta en fiscalización", "topic": "Operaciones sospechosas LA/FT", "difficulty": 3,
    "text": "Una gestora detecta facturas sin soporte económico, retiros inmediatos y transferencias fraccionadas a terceros incompatibles con la actividad declarada. Conserva las evidencias, pero no existe sentencia penal.",
    "questions": [
        {"stem": "¿Qué actuación procede aun sin sentencia penal?", "options": {"A": "Generar el ROS y remitirlo al competente.", "B": "Esperar una condena.", "C": "Archivar el hallazgo."}, "correct_key": "A", "rationale": "Fiscalización genera ROS al detectar presuntas operaciones inusuales o sospechosas de LA/FT.", "source_ref": "Resolución DIAN 69 de 2021 (Compilación Jurídica DIAN)."},
        {"stem": "¿Qué elementos justifican principalmente la sospecha?", "options": {"A": "Falta de soporte, retiros inmediatos y fraccionamiento incompatible.", "B": "El simple uso de bancos.", "C": "La falta de sentencia."}, "correct_key": "A", "rationale": "La combinación aporta señales objetivas y el ROS no exige certeza penal.", "source_ref": "Resoluciones DIAN 69 y 70 de 2021."},
        {"stem": "Tras el análisis institucional, ¿a qué entidad se envía el reporte?", "options": {"A": "A la UIAF.", "B": "Al Banco de la República.", "C": "A la Cámara de Comercio."}, "correct_key": "A", "rationale": "Los ROS analizados por la DIAN se envían a la UIAF.", "source_ref": "Resolución DIAN 70 de 2021, función 15."},
    ],
}]
