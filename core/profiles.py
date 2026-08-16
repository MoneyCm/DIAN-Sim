"""
Módulo de definición de Perfiles de Cargo para la DIAN.
Define las funciones esenciales y competencias asociadas para filtrar bancos de preguntas.
"""

PROFILES = {
    "Gestor II (Código 302, Grado 02)": {
        "description": "Perfil orientado a la gestión operativa de cartera, devoluciones y calidad de datos.",
        "functional_tracks": {
            "FUNCIONAL": [
                # Mapeo de Funciones Esenciales a Temas del Sistema
                "Gestión de Cartera",       # Gestión de Cartera
                "Cobro Coactivo",           # Campañas de Cobro
                "Devoluciones",             # Tramitar devoluciones/compensaciones
                "Auditoría Tributaria",     # Auditoría a Bancos / Grandes Contribuyentes
                "Representación Legal",     # Jurídica
                "Calidad de Datos",         # Corrección de Inconsistencias
                "Régimen Sancionatorio"     # Relacionado con sanciones en auditoría
            ],
            "INTEGRIDAD": [
                "Ética Pública",
                "Código Disciplinario",
                "Transparencia"
            ]
        },
        "behavioral_competencies": [
            "Comportamiento Ético", # Nivel 4
            "Adaptabilidad",        # Nivel 3
            "Comunicación Efectiva",# Nivel 3
            "Trabajo en Equipo",    # Nivel 3
            "Orientación al Logro",
            "Servicio al Ciudadano"
        ],
        "raw_text": """
        1. Funciones Esenciales (Específicas)
        Gestión de Cartera: Adelantar las diligencias de los procesos que le sean asignados...
        Representación Legal: Representar a la UAE DIAN en los procesos especiales...
        Depuración de Cuentas: Realizar las actividades tendientes a depurar la información...
        Devoluciones: Tramitar las solicitudes de devoluciones y/o compensaciones...
        Auditoría a Bancos: Desarrollar auditorías, capacitaciones...
        Calidad de Datos: Responder por la incorporación, la calidad y la unificación...
        Corrección de Inconsistencias: Corregir los datos inconsistentes...
        Campañas de Cobro: Desarrollar campañas de ejecución inmediata...
        Control de Grandes Contribuyentes: Aplicar mecanismos de control...
        Sistemas de Información (TI): Gestionar sistemas de información...
        """
    },
    "Gestor III (OPEC 236769)": {
        "description": "Gestor III, código 303, grado 3, ficha MERF AT-FL-3006. Perfil de fiscalización tributaria, aduanera y cambiaria vinculado a la OPEC 236769.",
        "selection_process": "DIAN 2676 - Ingreso",
        "source_status": "official_verified",
        "source_url": "https://www.dian.gov.co/dian/entidad/ManualdeFunciones/FT_TAH_1824_Gestor_III_AT_FL_3006.pdf",
        "functional_tracks": {
            "FUNCIONAL": [
                "Determinación y control tributario",
                "Régimen cambiario de competencia DIAN",
                "Fiscalización internacional",
                "Fiscalización aduanera",
            ],
            "INTEGRIDAD": [
                "Ética Pública",
                "Código Disciplinario",
                "Transparencia"
            ]
        },
        "behavioral_competencies": [
            "Comportamiento Ético - nivel 4",
            "Adaptabilidad - nivel 3",
            "Comunicación Efectiva - nivel 3",
            "Trabajo en Equipo - nivel 3",
        ],
        "raw_text": """
        Nivel: Profesional  Denominación: GESTOR III  Grado: 3  Código: 303  Número OPEC: 236769
        Proceso de Selección: DIAN 2676 - Ingreso
        Fuente del empleo: ficha MERF AT-FL-3006. La modalidad, vacantes y demás
        datos variables deben confirmarse en la ficha SIMO vigente de la OPEC.

        Propósito:
        AT-FL-3006. DESARROLLAR, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, INVESTIGACIONES PARA LA VERIFICACION DEL CUMPLIMIENTO DE OBLIGACIONES EN MATERIA TRIBUTARIA, ADUANERA O CAMBIARIA, ASI COMO LA DETECCION DE PRACTICAS TENDIENTES A LA ELUSION, EVASION, ABUSO, CONTRABANDO Y LAVADO DE ACTIVOS, DE ACUERDO CON LA NORMATIVA VIGENTE, LOS PROCEDIMIENTOS ESTABLECIDOS Y LAS DIRECTRICES INSTITUCIONALES.

        Funciones:
        1. HACER LA PRECRITICA Y CLASIFICACION DE LOS INSUMOS RECIBIDOS, ESTABLECIENDO LA PERTINENCIA DEL INICIO DE UNA INVESTIGACION, DE ACUERDO CON LOS PROCEDIMIENTOS Y LINEAMIENTOS INSTITUCIONALES.
        2. HACER EL ANALISIS PRELIMINAR DE LAS DENUNCIAS DE FISCALIZACION RECIBIDAS, ESTABLECIENDO LA PERTINENCIA DEL INICIO DE UNA ACCION DE FISCALIZACION, DE ACUERDO CON LA NORMATIVA VIGENTE, PROCEDIMIENTOS Y LINEAMIENTOS INSTITUCIONALES.
        3. REALIZAR INVESTIGACIONES PARA DETERMINAR EL CUMPLIMIENTO DE LAS OBLIGACIONES TRIBUTARIAS, ADUANERAS O CAMBIARIAS Y, EL REPORTE DE LAS OPERACIONES SOSPECHOSAS DE LAVADO DE ACTIVOS Y FINANCIACION DEL TERRORISMO, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, DE ACUERDO CON LA NORMATIVA VIGENTE, LAS DIRECTRICES INSTITUCIONALES Y LOS PROCEDIMIENTOS ESTABLECIDOS.
        4. PROFERIR LOS ACTOS ADMINISTRATIVOS DE TRAMITE, PREPARATORIOS Y DE FONDO REQUERIDOS DENTRO DEL PROCESO, DE ACUERDO CON LA NORMATIVA VIGENTE Y LOS PROCEDIMIENTOS ESTABLECIDOS.
        5. REVISAR TECNICA Y O JURIDICAMENTE, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, LOS EXPEDIENTES Y ASUNTOS ASIGNADOS PROPIOS DEL PROCESO, DE ACUERDO CON LA NORMATIVA VIGENTE Y LAS DIRECTRICES INSTITUCIONALES.
        6. PARTICIPAR EN LA EJECUCION DE ACCIONES DE FISCALIZACION, EN EL MARCO DE SU COMPETENCIA Y JURISDICCION, TENDIENTES A LA VERIFICACION DEL CUMPLIMIENTO DE LAS OBLIGACIONES TRIBUTARIAS, ADUANERAS O CAMBIARIAS, DE ACUERDO CON LA NORMATIVA VIGENTE, LINEAMIENTOS INSTITUCIONALES Y PROCEDIMIENTOS ESTABLECIDOS.
        7. ORGANIZAR LA INFORMACION Y PROPUESTAS DE ASUNTOS DE FISCALIZACION PARA PRESENTARLOS A CONSIDERACION DE LA REUNION DEL NIVEL DIRECTIVO DEL PROCESO DE FISCALIZACION Y LIQUIDACION PARA LA DECISION PERTINENTE.
        8. REALIZAR LA PRACTICA DE PRUEBAS SOLICITADAS POR UNA DEPENDENCIA DEL NIVEL CENTRAL O SECCIONAL, PARA QUE OBRE DENTRO DE UNA INVESTIGACION, DE ACUERDO CON LA NORMATIVA VIGENTE Y LOS PROCEDIMIENTOS ESTABLECIDOS.
        9. LAS SEÑALADAS COMO COMUNES A TODOS LOS EMPLEOS DE LA PLANTA DE PERSONAL DE LA ENTIDAD, INCLUIDAS EN LA RESOLUCION QUE ADOPTA O MODIFICA EL MANUAL Y LAS DEMAS ASIGNADAS POR AUTORIDAD COMPETENTE, DE ACUERDO CON EL NIVEL, GRADO DE RESPONSABILIDAD Y EL AREA DE DESEMPEÑO DEL EMPLEO.

        Requisitos:
        - Estudio: Título de PROFESIONAL en NBC: ADMINISTRACION, O NBC: CIENCIA POLITICA, RELACIONES INTERNACIONALES, O NBC: CONTADURIA PUBLICA, O NBC: DERECHO Y AFINES, O NBC: ECONOMIA, O NBC: INGENIERIA ADMINISTRATIVA Y AFINES, O NBC: INGENIERIA DE SISTEMAS, TELEMATICA Y AFINES, O NBC: INGENIERIA INDUSTRIAL Y AFINES, O NBC: INGENIERIA QUIMICA Y AFINES, O NBC: MATEMATICAS, ESTADISTICA Y AFINES.
        - Experiencia: Doce (12) meses de EXPERIENCIA PROFESIONAL RELACIONADA y Doce (12) meses de EXPERIENCIA PROFESIONAL.
        - Otros: Tarjeta Profesional en los casos señalados por la Ley.
        """
    },
    "Gestor III (OPEC 236739)": {
        "description": "Perfil Profesional Gestor III - Fiscalización y Liquidación (OPEC 236739).",
        "functional_tracks": {
            "FUNCIONAL": [
                "Fiscalización Tributaria",
                "Liquidación Oficial",
                "Procedimiento Administrativo",
                "Evasión y Elusión",
                "Régimen Probatorio",
                "Impuesto sobre la Renta",
                "IVA"
            ],
            "INTEGRIDAD": [
                "Ética Pública",
                "Código Disciplinario",
                "Transparencia"
            ]
        },
        "behavioral_competencies": [
            "Análisis de Datos", 
            "Pensamiento Crítico",
            "Resolución de Problemas",
            "Trabajo en Equipo",
            "Comunicación Asertiva"
        ],
        "raw_text": """
        Propósito: DESARROLLAR PROCESOS DE FISCALIZACIÓN Y LIQUIDACIÓN...
        Funciones:
        - PROFERIR ACTOS ADMINISTRATIVOS DE DETERMINACIÓN DE TRIBUTOS...
        - RESOLVER RECURSOS EN LA VÍA GUBERNATIVA...
        - ADELANTAR INVESTIGACIONES TRIBUTARIAS...
        """
    }
}

def get_profile_topics(profile_name: str) -> list[str]:
    """Retorna una lista plana de todos los temas asociados a un perfil."""
    if profile_name not in PROFILES:
        return []
    
    p = PROFILES[profile_name]
    topics = []
    
    # Add Functional Topics
    if "functional_tracks" in p:
        for track_list in p["functional_tracks"].values():
            topics.extend(track_list)
            
    # Add Behavioral Competencies (often treated as Topics in our simple model)
    if "behavioral_competencies" in p:
        topics.extend(p["behavioral_competencies"])
        
    return list(set(topics))
