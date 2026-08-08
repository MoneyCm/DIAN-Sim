"""Matriz provisional de fuentes oficiales para cualquier OPEC.

No declara que exista una guía específica: separa los documentos oficiales
transversales de las páginas que deben vigilarse hasta que CNSC publique la GOA.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import unicodedata


@dataclass(frozen=True)
class OfficialSource:
    area: str
    title: str
    url: str
    reason: str
    status: str = "oficial_disponible"

    def as_dict(self) -> dict:
        return asdict(self)


CNSC_CONVOCATORIAS = OfficialSource(
    "Reglas del concurso", "CNSC · Convocatorias, acuerdos, anexos y guías",
    "https://www.cnsc.gov.co/convocatorias",
    "Vigilar la publicación de acuerdos, anexos técnicos, ejes y GOA.", "monitorear_guia",
)
CNSC_PROYECTOS = OfficialSource(
    "Reglas del concurso", "CNSC · Proyectos de acuerdos y anexos",
    "https://www.cnsc.gov.co/proyecto-de-acuerdos-y-anexos-de-nuevos-procesos-de-seleccion",
    "Consultar reglas provisionales mientras se formaliza el proceso.", "monitorear_guia",
)
SIMO = OfficialSource(
    "Ficha del empleo", "SIMO · Oferta Pública de Empleos de Carrera",
    "https://simo.cnsc.gov.co/", "Fuente primaria de propósito, funciones y requisitos de la OPEC.",
)
DECRETO_1083 = OfficialSource(
    "Empleo público", "Decreto 1083 de 2015 · Gestor Normativo Función Pública",
    "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=62866",
    "Competencias laborales, empleo público, MIPG y reglas transversales.",
)
MIPG = OfficialSource(
    "Gestión pública", "Manual Operativo MIPG · Función Pública",
    "https://www1.funcionpublica.gov.co/documents/28587410/34112007/2023-03-21_Manual_operativo_mipg_5V.pdf/dbe560cc-e81d-bd7b-b23f-075184e029c6?t=1679509602732",
    "Planeación, riesgos, indicadores, información, control y mejora institucional.",
)
MRAE = OfficialSource(
    "Tecnologías de información", "Marco de Referencia de Arquitectura Empresarial · MinTIC",
    "https://gobiernodigital.mintic.gov.co/portal/403294:Marco-de-Referencia-de-Arquitectura-Empresarial",
    "Arquitectura empresarial, gobierno y gestión de TI, información y servicios.",
)
MINTIC_INSTRUMENTOS = OfficialSource(
    "Tecnologías de información", "Guías, instrumentos y lineamientos · MinTIC",
    "https://www.mintic.gov.co/portal/715/articles-198952_anexo_1_3_guias_instrumentos_lineamientos.pdf",
    "PETI, MSPI, arquitectura empresarial, datos e interoperabilidad.",
)
MRAE_NORMA = OfficialSource(
    "Tecnologías de información", "Resolución MinTIC 1978 de 2023 · MRAE v3",
    "https://normograma.mintic.gov.co/mintic/compilacion/docs/resolucion_mintic_1978_2023.htm",
    "Adopción normativa del Marco de Referencia de Arquitectura Empresarial v3.",
)
CCE_SERVICIOS = OfficialSource(
    "Contratación pública", "Guía de contratación de prestación de servicios · Colombia Compra Eficiente",
    "https://www.colombiacompra.gov.co/sites/cce_public/files/files_2020/cce-eicp-gi-21_guia_contratacion_prestacion_de_servicios_v1_03-03-2023_1.pdf",
    "Contratación, vigilancia, obligaciones y supervisión de servicios.",
)

ENTITY_PORTALS = {
    "ADRES-ABIERTO": ("ADRES · Portal institucional", "https://www.adres.gov.co/"),
    "ALIMENTACION-ESCOLAR-ABIERTO": ("Alimentos para Aprender · Portal institucional", "https://www.alimentosparaaprender.gov.co/"),
    "TERRITORIAL-12-BOLIVAR-2685": ("Gobernación de Bolívar · Portal institucional", "https://www.bolivar.gov.co/"),
}


def _normalise(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def _function_text(opec) -> str:
    return " ".join(str(item) for item in (getattr(opec, "functions", None) or []))


def build_official_source_matrix(opec, competition=None) -> list[dict]:
    """Return a deduplicated, official-only starting matrix for an OPEC."""
    sources = [SIMO, CNSC_CONVOCATORIAS, CNSC_PROYECTOS, DECRETO_1083, MIPG]
    code = str(getattr(competition, "code", "") or "")
    if code in ENTITY_PORTALS:
        title, url = ENTITY_PORTALS[code]
        sources.append(OfficialSource(
            "Entidad convocante", title, url,
            "Revisar manuales, planes, políticas, normograma y publicaciones institucionales.",
            "monitorear_entidad",
        ))

    text = _normalise(" ".join([
        getattr(opec, "job_title", "") or "", getattr(opec, "purpose", "") or "",
        _function_text(opec), getattr(opec, "requirements", "") or "",
    ]))
    if any(term in text for term in (
        "tecnologia", "software", "sistema", "arquitectura", "seguridad", "privacidad",
        "datos", "interoperabilidad", "peti", "proveedor de servicios de tecnologia",
    )):
        sources.extend([MRAE, MINTIC_INSTRUMENTOS, MRAE_NORMA])
    if any(term in text for term in ("contrato", "contratacion", "proveedor", "supervision")):
        sources.append(CCE_SERVICIOS)

    unique = {source.url: source for source in sources}
    return [source.as_dict() for source in unique.values()]


def source_titles_for_function(function_text: str) -> list[str]:
    """Attach relevant official starting references to provisional questions."""
    text = _normalise(function_text)
    titles = [SIMO.title, DECRETO_1083.title]
    if any(term in text for term in ("plan", "programa", "proyecto", "meta", "indicador", "riesgo")):
        titles.append(MIPG.title)
    if any(term in text for term in (
        "tecnologia", "software", "sistema", "arquitectura", "seguridad", "privacidad",
        "datos", "interoperabilidad", "peti",
    )):
        titles.extend([MRAE.title, MINTIC_INSTRUMENTOS.title])
    if any(term in text for term in ("contrato", "contratacion", "proveedor", "supervision")):
        titles.append(CCE_SERVICIOS.title)
    return list(dict.fromkeys(titles))
