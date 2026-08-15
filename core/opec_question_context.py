"""Explainable links between a bank question and an OPEC manual function."""

from __future__ import annotations

import re


_EXPLICIT_FUNCTION = re.compile(
    r"\b(?:opec\s*\d+\s*[-·:]?\s*)?f(?:uncion)?\s*0?(\d{1,2})\b", re.IGNORECASE
)
_SOURCE_FUNCTION = re.compile(r"\bfunci[oó]n\s*0?(\d{1,2})\b", re.IGNORECASE)


def function_number_for_question(question, opec_number: object = "") -> int | None:
    """Return only an explicit function mapping; never infer it from vague words."""
    case = getattr(question, "case_study", None)
    case_id = str(getattr(case, "id", None) or getattr(question, "case_id", "") or "")
    if str(opec_number) == "236769" and case_id:
        try:
            from core.opec_236769 import function_number_for_case_id

            return function_number_for_case_id(case_id)
        except ValueError:
            pass

    text = " ".join(
        str(getattr(question, field, "") or "")
        for field in ("micro_competencia", "topic", "source_refs")
    )
    match = _EXPLICIT_FUNCTION.search(text) or _SOURCE_FUNCTION.search(text)
    return int(match.group(1)) if match else None


def manual_function_context(question, opec_number: object, functions) -> dict | None:
    """Return a display-ready, explicit mapping to the active OPEC manual."""
    number = function_number_for_question(question, opec_number)
    clean_functions = [str(item).strip() for item in (functions or []) if str(item).strip()]
    if number is None or not 1 <= number <= len(clean_functions):
        return None
    return {"number": number, "text": clean_functions[number - 1]}


def matches_manual_function_filter(question, opec_number: object, selected_numbers) -> bool:
    """Keep a question when no manual filter is set or its mapping is selected."""
    wanted = {int(item) for item in (selected_numbers or [])}
    return not wanted or function_number_for_question(question, opec_number) in wanted
