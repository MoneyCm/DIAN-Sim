"""Common-function GOA cases for OPEC 236769 (function gap F3).

The scenarios are limited to duties expressly listed in article 6 of DIAN
Resolution 67 of 2024 and the AT-FL-3006 job profile.
"""


def q(stem, a, b, c, rationale, numerals):
    return {
        "stem": stem,
        "options": {"A": a, "B": b, "C": c},
        "correct_key": "A",
        "rationale": rationale,
        "source_ref": (
            f"Resolución DIAN 000067 de 2024, artículo 6, numeral(es) {numerals}; "
            "ficha de empleo AT-FL-3006 Gestor III, funciones comunes "
            "(Compilación Jurídica y Manual de Funciones DIAN, consulta 2026-08-01)."
        ),
    }


CURATED_GAP_CASES_PHASE16 = [
    {
        "id": "goa-236769-f3-riesgos-indicadores-mejora-01",
        "title": "Seguimiento de un programa y tratamiento de riesgos",
        "topic": "F3 - Planes, indicadores, riesgos y mejora",
        "difficulty": 3,
        "text": (
            "Durante el seguimiento de un programa de fiscalización, el indicador definido muestra "
            "un avance inferior al esperado y varios expedientes se aproximan a términos relevantes. "
            "Un integrante propone excluir del cálculo los casos atrasados para presentar la meta como "
            "cumplida y esperar al cierre anual antes de analizar el riesgo. También se han repetido "
            "fallas del flujo de trabajo que afectan el sistema de gestión de la dependencia."
        ),
        "questions": [
            q(
                "¿Cómo debe manejarse la desviación observada en el indicador del programa?",
                "Mantener la información real, efectuar el seguimiento y evaluación y promover los ajustes del plan conforme a los procedimientos establecidos.",
                "Excluir los expedientes atrasados aunque integren la medición aprobada.",
                "Eliminar el indicador porque una desviación impide cualquier acción de mejora.",
                "La función común comprende formular, seguir, evaluar y ajustar planes, programas o proyectos, incluidos sus indicadores de gestión. Esto exige trabajar con el resultado real y tramitar los ajustes por las vías establecidas.",
                "2",
            ),
            q(
                "¿Qué aporte funcional corresponde frente al riesgo de vencimiento detectado?",
                "Participar en estrategias, metodologías o mejores prácticas dirigidas a detectar y mitigar el riesgo dentro del proceso y la normativa aplicable.",
                "Ocultarlo hasta que ocurra el vencimiento para no alterar la programación.",
                "Modificar individualmente los términos legales de los expedientes para ampliar el plazo.",
                "La resolución asigna como función común participar en la elaboración y desarrollo de estrategias, propuestas de auditoría, metodologías y mejores prácticas para detección y mitigación de riesgos.",
                "3",
            ),
            q(
                "¿Qué debe hacerse con las fallas repetidas que afectan el sistema de gestión?",
                "Ejecutar las acciones de implementación, mantenimiento o mejora que correspondan, respetando la normativa y los lineamientos institucionales.",
                "Crear un procedimiento paralelo sin autorización ni trazabilidad.",
                "Ignorarlas porque la mejora de los sistemas de gestión no forma parte de las funciones comunes.",
                "El artículo 6 incluye expresamente las acciones requeridas para implementar, mantener y mejorar los sistemas de gestión de la Entidad, siempre bajo la normativa y los lineamientos establecidos.",
                "1",
            ),
        ],
    },
    {
        "id": "goa-236769-f3-seguridad-datos-sistemas-01",
        "title": "Protección de la información de una investigación",
        "topic": "F3 - Seguridad de información, datos y sistemas corporativos",
        "difficulty": 3,
        "text": (
            "Un expediente de fiscalización contiene identificaciones, datos de contacto, certificados "
            "bancarios y análisis del investigado. Un servidor que no participa en el caso pide que le "
            "envíen la carpeta completa a su correo personal para revisarla desde casa. Al mismo tiempo, "
            "un usuario externo solicita orientación sobre el trámite y el sistema corporativo presenta "
            "un error recurrente de acceso al expediente."
        ),
        "questions": [
            q(
                "¿Cómo debe responder el gestor a la solicitud de remitir el expediente al correo personal?",
                "Aplicar los lineamientos institucionales de seguridad y protección de datos antes de cualquier acceso o transmisión y no eludirlos por conveniencia.",
                "Enviar toda la carpeta porque cualquier servidor público puede usar cuentas personales para datos de fiscalización.",
                "Publicar el expediente para evitar tener que evaluar quién puede acceder.",
                "La seguridad de la información y la protección de datos personales son funciones comunes expresas. La resolución no autoriza excepciones por rapidez ni sustituye los lineamientos institucionales de acceso y transmisión.",
                "11",
            ),
            q(
                "¿Qué conducta corresponde frente al usuario externo que solicita orientación?",
                "Orientarlo dentro de la normativa, la competencia y los lineamientos institucionales, preservando las reglas aplicables a la información del expediente.",
                "Revelarle los datos bancarios del investigado para demostrar que la dependencia conoce el caso.",
                "Negarse a brindar cualquier orientación porque esta nunca es función de un empleo profesional.",
                "La orientación a usuarios internos y externos es una función común, pero debe darse según la competencia, la normativa y los lineamientos; se mantiene además el deber de aplicar las reglas de seguridad y datos personales.",
                "4 y 11",
            ),
            q(
                "¿Cómo debe canalizarse el error recurrente del sistema corporativo que afecta la consulta del expediente?",
                "Gestionar su ajuste o mantenimiento conforme a las políticas, procedimientos, planes y necesidades institucionales identificadas.",
                "Copiar permanentemente los expedientes a una base personal no autorizada.",
                "Alterar directamente el sistema en producción sin seguir política o procedimiento alguno.",
                "La resolución contempla gestionar la creación, implantación, ajuste y mantenimiento de los sistemas corporativos del proceso, con sujeción a las políticas, procedimientos y planes vigentes.",
                "8",
            ),
        ],
    },
    {
        "id": "goa-236769-f3-documentos-pqrs-informes-01",
        "title": "Organización documental y atención de asuntos asignados",
        "topic": "F3 - Gestión documental, peticiones e informes",
        "difficulty": 3,
        "text": (
            "Al recibir una investigación tributaria, el gestor encuentra actos, soportes de prueba y "
            "constancias de notificación distribuidos entre la unidad documental y carpetas de trabajo, "
            "mientras el inventario documental está desactualizado. Además, le asignan una denuncia "
            "relacionada con el mismo subproceso y debe preparar un informe rutinario sobre la gestión "
            "realizada."
        ),
        "questions": [
            q(
                "¿Qué actuación corresponde frente a los documentos dispersos y el inventario desactualizado?",
                "Organizar, conservar, usar y manejar adecuadamente la documentación y actualizar el inventario de la producción documental derivada de sus funciones.",
                "Eliminar los soportes que no estén mencionados en el inventario actual.",
                "Mantener versiones definitivas únicamente en carpetas personales sin incorporarlas a la gestión documental.",
                "El numeral 12 ordena realizar las acciones necesarias para la adecuada gestión de documentos y archivos y mantener actualizado el inventario documental producido en el ejercicio de las funciones.",
                "12",
            ),
            q(
                "¿Cómo debe proceder con la denuncia que le fue asignada?",
                "Atenderla de acuerdo con el proceso o subproceso de desempeño y con la normativa y los procedimientos vigentes.",
                "Archivarla sin análisis porque las denuncias no aparecen en las funciones comunes.",
                "Resolverla aplicando instrucciones informales contrarias al procedimiento vigente.",
                "La atención de peticiones, quejas, sugerencias, reclamos y denuncias asignadas es una función común expresa y debe cumplirse según el proceso, la normativa y el procedimiento aplicable.",
                "6",
            ),
            q(
                "¿Con qué criterio debe elaborar el informe rutinario solicitado?",
                "Proyectarlo conforme a la normativa, los procedimientos y los lineamientos institucionales aplicables al subproceso.",
                "Incluir resultados no verificados para mejorar artificialmente el reporte de gestión.",
                "Rechazar su elaboración porque proyectar informes habituales corresponde exclusivamente al nivel directivo.",
                "La resolución incluye entre las funciones comunes proyectar actos, documentos e informes de asuntos rutinarios o habituales del proceso, bajo las reglas y lineamientos vigentes.",
                "7",
            ),
        ],
    },
]
