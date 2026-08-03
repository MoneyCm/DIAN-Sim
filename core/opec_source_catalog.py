"""Curated official study sources mapped to known DIAN OPEC functions.

The catalogue complements, but never replaces, the sources attached to verified
questions.  It is deliberately limited to documents recorded in the project's
official-source audit.
"""

from __future__ import annotations

import unicodedata


FICHA_236769 = "Ficha de empleo AT-FL-3006 · OPEC 236769 (funciones y alcance del cargo)"
CPACA = "Ley 1437 de 2011 (CPACA) · procedimiento administrativo, pruebas, actos y recursos"
ESTATUTO = "Estatuto Tributario DIAN · fiscalización, pruebas, devoluciones, sanciones y recursos"
ADUANAS = "Decreto 1165 de 2019 · régimen de aduanas y control posterior"
ADUANAS_SANCION = "Ley 2586 de 2026 · procedimiento y régimen sancionatorio aduanero"
CAMBIARIO = "Decreto Ley 2245 de 2011 · procedimiento sancionatorio cambiario DIAN"
PR_CAMBIARIO = "PR-COA-0223 v6 · investigación de infracciones cambiarias DIAN"
PR_TRIBUTARIO = "PR-COT-0432 v3 · liquidación provisional DIAN"
LMDP = "Listado Maestro de Documentos Públicos DIAN · verificar versión vigente del procedimiento"
ESTRUCTURA = "Decreto 1742 de 2020 · estructura y competencias de dependencias DIAN"
MIPG = "Manual Operativo MIPG 6.1 · gestión, riesgos, indicadores y mejora"


def _normalise(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def sources_for_opec_function(opec_number: object, function: object) -> list[str]:
    """Return official starting sources for a documented OPEC function."""
    if str(opec_number or "").strip() != "236769":
        return []

    text = _normalise(function)
    sources = [FICHA_236769]

    if any(term in text for term in ("denuncia", "pertinencia", "denfis")):
        sources.extend([ESTATUTO, CPACA, LMDP])
    elif any(term in text for term in ("insumo", "precritica", "persuasiva")):
        sources.extend([ESTATUTO, CPACA, LMDP])
    elif any(term in text for term in ("reunion", "directiva", "tecnica", "juridica")):
        sources.extend([ESTRUCTURA, MIPG, CPACA])
    elif any(term in text for term in ("prueba", "exterior", "dependencia")):
        sources.extend([CPACA, ESTATUTO, LMDP])
    elif any(term in text for term in ("cambi", "lavado", "la/ft", "operacion sospechosa")):
        sources.extend([PR_CAMBIARIO, CAMBIARIO, LMDP])
    elif any(term in text for term in ("aduan", "control posterior", "contrabando")):
        sources.extend([ADUANAS, ADUANAS_SANCION, LMDP])
    elif any(term in text for term in ("acto", "notificacion", "recurso", "liquidacion", "fiscalizacion")):
        sources.extend([ESTATUTO, CPACA, PR_TRIBUTARIO])
    elif any(term in text for term in ("indicador", "riesgo", "documental", "dato", "sistema")):
        sources.extend([MIPG, ESTRUCTURA, LMDP])
    else:
        sources.extend([CPACA, ESTRUCTURA])

    return list(dict.fromkeys(sources))
