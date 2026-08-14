"""Source-first evidence checks for study-bank questions.

These checks do not decide legal correctness.  They distinguish a direct
official citation from a recognised legal anchor and from an untraceable claim,
so AI quality scores can never be mistaken for a source decision.
"""

from __future__ import annotations

import re
import unicodedata


DIAN_ESTATUTO_FACTURACION_URL = (
    "https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/estatuto-tributario/"
)
SUIN_DECRETO_1165_URL = "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30036618"
SUIN_CPACA_URL = "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1680117"
OFFICIAL_DOMAINS = (
    "dian.gov.co",
    "normograma.dian.gov.co",
    "cnsc.gov.co",
    "simo.cnsc.gov.co",
    "suin-juriscol.gov.co",
    "funcionpublica.gov.co",
)


def _normalise(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def _article_anchor(text: str) -> str | None:
    match = re.search(r"\b(?:articulo|art\.?)[\s:.-]*(\d+(?:-\d+)?)\b", text)
    return match.group(1) if match else None


def assess_source_evidence(question) -> dict:
    """Return explainable provenance evidence without approving the question."""
    source = str(getattr(question, "source_refs", "") or "").strip()
    combined = " ".join((
        source,
        str(getattr(question, "stem", "") or ""),
        str(getattr(question, "rationale", "") or ""),
    ))
    text = _normalise(combined)
    article = _article_anchor(text)

    if not source:
        return {
            "status": "UNTRACEABLE",
            "article": article,
            "official_url": "",
            "reason": "No declara fuente para contrastar.",
        }
    if any(domain in text for domain in OFFICIAL_DOMAINS):
        return {
            "status": "DIRECT_OFFICIAL_SOURCE",
            "article": article,
            "official_url": "",
            "reason": "Incluye una referencia a un portal oficial; confirmar el artículo y la vigencia.",
        }
    if "estatuto tributario" in text and article:
        return {
            "status": "DIRECT_OFFICIAL_SOURCE" if article == "616-1" else "OFFICIAL_CATALOG_MATCH",
            "article": article,
            "official_url": DIAN_ESTATUTO_FACTURACION_URL if article == "616-1" else "",
            "reason": (
                "Ancla el artículo en el micrositio oficial DIAN; requiere contrastar la afirmación con el texto vigente."
                if article == "616-1" else
                "Reconoce una norma tributaria y artículo; requiere contrastar la afirmación con el texto vigente."
            ),
        }
    if "decreto 1165" in text and article:
        return {
            "status": "DIRECT_OFFICIAL_SOURCE",
            "article": article,
            "official_url": SUIN_DECRETO_1165_URL,
            "reason": "Ancla el artículo en el texto oficial del Decreto 1165; requiere contrastar la afirmación con la versión vigente.",
        }
    if "ley 1437" in text or "cpaca" in text:
        return {
            "status": "DIRECT_OFFICIAL_SOURCE",
            "article": article,
            "official_url": SUIN_CPACA_URL,
            "reason": "Ancla el artículo en el texto oficial del CPACA; requiere contrastar la afirmación con la versión vigente.",
        }
    return {
        "status": "UNTRACEABLE",
        "article": article,
        "official_url": "",
        "reason": "No contiene fuente oficial directa ni ancla normativa reconocible.",
    }


def record_source_evidence(question) -> dict:
    """Persist the reproducible source check while leaving study status unchanged."""
    evidence = assess_source_evidence(question)
    report = dict(getattr(question, "quality_report", None) or {})
    report["source_evidence"] = evidence
    question.quality_report = report
    return evidence
