"""Source-first evidence checks for study-bank questions.

These checks do not decide legal correctness.  They distinguish a direct
official citation from a recognised legal anchor and from an untraceable claim,
so AI quality scores can never be mistaken for a source decision.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


SOURCE_EVIDENCE_VERSION = "official-links-v3"


DIAN_ESTATUTO_FACTURACION_URL = (
    "https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/estatuto-tributario/"
)
SUIN_DECRETO_1165_URL = "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30036618"
SUIN_CPACA_URL = "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1680117"
SUIN_ESTATUTO_TRIBUTARIO_URL = "https://suin-juriscol.gov.co/viewDocument.asp?id=1132325"
SUIN_DECRETO_1625_URL = (
    "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F30030361"
)
FUNCION_PUBLICA_DECRETO_1742_URL = (
    "https://www1.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=153986"
)
OFFICIAL_DOMAINS = (
    "dian.gov.co",
    "normograma.dian.gov.co",
    "cnsc.gov.co",
    "simo.cnsc.gov.co",
    "suin-juriscol.gov.co",
    "funcionpublica.gov.co",
)
VERIFIED_SOURCE_STATUSES = {"official_current", "official_verified"}


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
            "status": "DIRECT_OFFICIAL_SOURCE",
            "article": article,
            "official_url": (
                DIAN_ESTATUTO_FACTURACION_URL
                if article == "616-1"
                else SUIN_ESTATUTO_TRIBUTARIO_URL
            ),
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
    if "decreto 1625" in text:
        return {
            "status": "DIRECT_OFFICIAL_SOURCE",
            "article": article,
            "official_url": SUIN_DECRETO_1625_URL,
            "reason": "Enlaza el texto oficial del Decreto 1625; requiere contrastar la afirmaci\u00f3n y su vigencia.",
        }
    if "decreto 1742" in text:
        return {
            "status": "DIRECT_OFFICIAL_SOURCE",
            "article": article,
            "official_url": FUNCION_PUBLICA_DECRETO_1742_URL,
            "reason": "Enlaza el texto oficial de estructura de la DIAN; requiere contrastar la funci\u00f3n o competencia citada.",
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


def precise_source_verification_error(question) -> str | None:
    """Validate the persisted editorial proof that supports a question key.

    Detecting an official website is only an anchor.  Approval additionally
    requires an editor to record the exact locator, supporting excerpt,
    currency check, date and reviewer.  This deliberately does not ask an LLM
    to certify legal correctness.
    """
    report = getattr(question, "quality_report", None)
    verification = report.get("source_verification") if isinstance(report, dict) else None
    if not isinstance(verification, dict):
        return "Falta la verificación normativa individual de la fuente."

    status = str(verification.get("status", "")).strip().casefold()
    if status not in VERIFIED_SOURCE_STATUSES:
        return "La fuente no está marcada como oficial y vigente."

    url = str(verification.get("url", "")).strip()
    host = (urlparse(url).hostname or "").casefold()
    if not host or not any(host == domain or host.endswith(f".{domain}") for domain in OFFICIAL_DOMAINS):
        return "La verificación debe enlazar una URL oficial."

    if not str(verification.get("locator", "")).strip():
        return "Falta el artículo, numeral o página exacta que sustenta la clave."
    if len(str(verification.get("supporting_excerpt", "")).strip()) < 10:
        return "Falta un fragmento breve de soporte contrastado con la fuente."
    if not str(verification.get("verified_on", "")).strip():
        return "Falta la fecha de verificación normativa."
    if not str(verification.get("verified_by", "")).strip():
        return "Falta identificar el proceso o responsable de la verificación."
    return None


def has_precise_source_verification(question) -> bool:
    """Return whether the question carries complete, official source proof."""
    return precise_source_verification_error(question) is None
