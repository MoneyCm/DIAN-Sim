"""Explicit function mapping for the reviewed Gestor III OPEC 236769 GOA cases."""

from __future__ import annotations


CASE_FUNCTIONS = {
    "goa-236769-f4-priorizacion-pta-apd-02": 4,
    "goa-236769-aduanas-control-posterior-01": 5,
    "goa-236769-cambiario-declaraciones-01": 7,
    "goa-236769-cambiario-canalizacion-01": 7,
    "goa-236769-internacional-doc-01": 5,
    "goa-236769-denuncias-precritica-01": 2,
    "goa-236769-laft-ros-01": 7,
    "goa-236769-pruebas-expediente-01": 8,
    "goa-236769-pruebas-inspeccion-01": 8,
    "goa-236769-aduanas-facultades-01": 5,
    "goa-236769-contrabando-denuncia-01": 1,
    "goa-236769-internacional-plena-01": 5,
    "goa-236769-internacional-umbral-01": 5,
    "goa-236769-aduanas-analisis-integral-01": 5,
    "goa-236769-cambiario-canalizacion-ficticia-01": 7,
    "goa-236769-liquidacion-provisional-flujo-01": 5,
    "goa-236769-garantia-competencia-01": 6,
    "goa-236769-apd-evidencia-cierre-01": 5,
    "goa-236769-apd-ley2586-01": 5,
    "goa-236769-registro-prueba-ley2586-01": 8,
    "goa-236769-precritica-persuasion-ley2586-01": 2,
    "goa-236769-cambiario-inicio-reserva-01": 7,
    "goa-236769-cambiario-visita-prueba-01": 8,
    "goa-236769-cambiario-cargos-descargos-01": 7,
    "goa-236769-tributario-facultades-01": 5,
    "goa-236769-tributario-valoracion-prueba-01": 8,
    "goa-236769-tributario-inspeccion-01": 5,
    "goa-236769-tributario-requerimiento-respuesta-01": 6,
    "goa-236769-tributario-ampliacion-01": 6,
    "goa-236769-tributario-correspondencia-liquidacion-01": 6,
    "goa-236769-devoluciones-terminos-compensacion-01": 5,
    "goa-236769-devoluciones-inadmision-suspension-01": 5,
    "goa-236769-devoluciones-investigacion-sancion-01": 5,
    "goa-236769-cpaca-competencia-remision-01": 6,
    "goa-236769-cpaca-impedimento-01": 6,
    "goa-236769-cpaca-prueba-decision-01": 6,
    "goa-236769-tributario-notificacion-formas-direccion-01": 6,
    "goa-236769-tributario-notificacion-electronica-01": 6,
    "goa-236769-tributario-reconsideracion-01": 6,
    "goa-236769-f4-propuesta-apd-directivo-01": 4,
    "goa-236769-f9-revision-liquidacion-provisional-01": 9,
    "goa-236769-f9-revision-expediente-decision-01": 9,
    "goa-236769-prueba-interdependencia-01": 8,
    "goa-236769-prueba-exterior-rilo-01": 8,
    "goa-236769-denfis-analisis-preliminar-01": 1,
    "goa-236769-f3-riesgos-indicadores-mejora-01": 3,
    "goa-236769-f3-seguridad-datos-sistemas-01": 3,
    "goa-236769-f3-documentos-pqrs-informes-01": 3,
}


def function_number_for_case_id(case_id: str) -> int:
    try:
        return CASE_FUNCTIONS[case_id]
    except KeyError as exc:
        raise ValueError(f"Caso curado sin función OPEC 236769: {case_id}") from exc


def function_label(case_id: str, topic: str) -> str:
    return f"OPEC 236769 F{function_number_for_case_id(case_id)} · {topic}"
