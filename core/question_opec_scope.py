"""Resolve the explicit OPEC scope of shared-bank questions.

Competition scope is not enough: one CNSC process can contain many OPECs. An
unscoped question is intentionally excluded from personalised practice until a
reviewer or import process records its OPEC.
"""

from __future__ import annotations

import re


OPEC_TEXT = re.compile(r"\bOPEC\s*[:#-]?\s*(\d{5,7})\b", re.I)
OPEC_IDENTIFIER = re.compile(r"(?:^|[-_])(?:goa|case|opec)[-_]?(\d{5,7})(?:[-_]|$)", re.I)


def _declared_scope(question) -> str | None:
    report = getattr(question, "quality_report", None)
    if not isinstance(report, dict):
        return None
    scope = report.get("scope")
    if isinstance(scope, dict) and scope.get("opec_number"):
        return str(scope["opec_number"]).strip()
    if report.get("opec_number"):
        return str(report["opec_number"]).strip()
    return None


def question_opec_number(question) -> str | None:
    """Return one unambiguous OPEC number, or None when evidence is missing."""
    declared = _declared_scope(question)
    if declared:
        return declared

    case = getattr(question, "case_study", None)
    identifiers = (
        getattr(case, "id", None),
        getattr(question, "case_id", None),
        getattr(question, "question_id", None),
    )
    for value in identifiers:
        match = OPEC_IDENTIFIER.search(str(value or ""))
        if match:
            return match.group(1)

    values = (
        getattr(question, "topic", None),
        getattr(question, "micro_competencia", None),
        getattr(question, "competency", None),
        getattr(question, "source_refs", None),
        getattr(question, "stem", None),
        getattr(case, "title", None),
        getattr(case, "topic", None),
    )
    discovered = {
        match.group(1)
        for value in values
        for match in OPEC_TEXT.finditer(str(value or ""))
    }
    return next(iter(discovered)) if len(discovered) == 1 else None


def question_matches_opec(question, opec_number: object) -> bool:
    target = str(opec_number or "").strip()
    return bool(target) and question_opec_number(question) == target


def stamp_question_opec(question, opec_number: object) -> None:
    """Persist scope inside existing JSON metadata without a schema migration."""
    target = str(opec_number or "").strip()
    if not target:
        raise ValueError("Se requiere un número OPEC para asignar la pregunta.")
    report = dict(getattr(question, "quality_report", None) or {})
    scope = dict(report.get("scope") or {})
    scope["opec_number"] = target
    report["scope"] = scope
    question.quality_report = report
