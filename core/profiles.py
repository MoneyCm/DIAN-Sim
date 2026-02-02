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
        "description": "Perfil Profesional especializado en Fiscalización, Investigación Tributaria y Detección de Evasión.",
        "functional_tracks": {
            "FUNCIONAL": [
                "Fiscalización",
                "Procedimiento Tributario",
                "Investigación",
                "Evasión",
                "Lavado de Activos",
                "Régimen Sancionatorio", 
                "Pruebas",
                "Actos Administrativos"
            ],
            "INTEGRIDAD": [
                "Ética Pública",
                "Código Disciplinario",
                "Transparencia"
            ]
        },
        "behavioral_competencies": [
            "Análisis de Información", 
            "Pensamiento Crítico",
            "Toma de Decisiones",
            "Trabajo en Equipo",
            "Comunicación Efectiva"
        ],
        "raw_text": """
        Propósito: DESARROLLAR INVESTIGACIONES PARA LA VERIFICACION DEL CUMPLIMIENTO DE OBLIGACIONES...
        Funciones:
        - HACER EL ANALISIS PRELIMINAR DE LAS DENUNCIAS DE FISCALIZACION...
        - HACER LA PRECRITICA Y CLASIFICACION DE LOS INSUMOS...
        - ORGANIZAR LA INFORMACION Y PROPUESTAS DE ASUNTOS DE FISCALIZACION...
        - PARTICIPAR EN LA EJECUCION DE ACCIONES DE FISCALIZACION...
        - PROFERIR LOS ACTOS ADMINISTRATIVOS DE TRAMITE...
        - REALIZAR INVESTIGACIONES PARA DETERMINAR EL CUMPLIMIENTO...
        - REALIZAR LA PRACTICA DE PRUEBAS SOLICITADAS...
        - REVISAR TECNICA Y O JURIDICAMENTE LOS EXPEDIENTES...
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
