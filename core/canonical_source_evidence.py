"""Canonical citation lookup kept separate for safe Streamlit hot reloads."""

from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import func, inspect
from sqlalchemy.exc import SQLAlchemyError

from core.source_evidence import OFFICIAL_DOMAINS
from db.models import QuestionCitation, SourceDocument


def _is_official_url(value: object) -> bool:
    host = (urlparse(str(value or "").strip()).hostname or "").casefold()
    return bool(host) and any(
        host == domain or host.endswith(f".{domain}")
        for domain in OFFICIAL_DOMAINS
    )


def canonical_source_verification(db, question_id: str) -> dict:
    """Load the strongest current canonical citation for one question."""
    try:
        inspector = inspect(db.connection())
        required = {"question_citations", "source_documents"}
        if not all(inspector.has_table(table) for table in required):
            return {}
        rows = (
            db.query(QuestionCitation, SourceDocument)
            .join(
                SourceDocument,
                SourceDocument.id == QuestionCitation.source_document_id,
            )
            .filter(
                QuestionCitation.question_id == str(question_id),
                QuestionCitation.supports_key.is_(True),
                QuestionCitation.verified_at.is_not(None),
                func.length(func.trim(QuestionCitation.verified_by)) > 0,
                func.length(func.trim(QuestionCitation.locator)) > 0,
                func.length(func.trim(QuestionCitation.excerpt)) >= 10,
                SourceDocument.validity_status == "current",
                func.length(func.trim(SourceDocument.official_url)) > 0,
            )
            .order_by(QuestionCitation.verified_at.desc(), QuestionCitation.id.desc())
            .all()
        )
    except SQLAlchemyError:
        db.rollback()
        return {}

    for citation, document in rows:
        if not _is_official_url(document.official_url):
            continue
        verified_at = citation.verified_at
        return {
            "status": "official_current",
            "url": str(document.official_url).strip(),
            "locator": str(citation.locator).strip(),
            "supporting_excerpt": str(citation.excerpt).strip(),
            "verified_on": (
                verified_at.date().isoformat()
                if hasattr(verified_at, "date")
                else str(verified_at)
            ),
            "verified_by": str(citation.verified_by).strip(),
        }
    return {}
