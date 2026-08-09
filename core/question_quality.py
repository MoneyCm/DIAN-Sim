"""Deterministic, free quality checks for question-bank candidates."""

from __future__ import annotations

import re
from collections import Counter


def audit_question_structure(question) -> dict:
    """Return explainable checks without certifying factual correctness."""
    findings: list[dict[str, str]] = []

    def add(code: str, severity: str, message: str) -> None:
        findings.append({"code": code, "severity": severity, "message": message})

    stem = str(getattr(question, "stem", "") or "").strip()
    rationale = str(getattr(question, "rationale", "") or "").strip()
    source = str(getattr(question, "source_refs", "") or "").strip()
    options = getattr(question, "options_json", None)
    correct = str(getattr(question, "correct_key", "") or "").strip().upper()
    difficulty = getattr(question, "difficulty", None)

    if len(stem) < 35:
        add("stem_too_short", "error", "El enunciado es demasiado corto para aportar contexto suficiente.")
    if not isinstance(options, dict) or len(options) != 3:
        add("invalid_options", "error", "La pregunta debe tener exactamente tres opciones.")
        option_values = []
    else:
        expected = {"A", "B", "C"}
        if set(options) != expected:
            add("invalid_option_keys", "error", "Las opciones deben identificarse como A, B y C.")
        option_values = [re.sub(r"\s+", " ", str(value or "").strip().lower()) for value in options.values()]
        if any(not value for value in option_values):
            add("empty_option", "error", "Hay una opción vacía.")
        if len(set(option_values)) != len(option_values):
            add("duplicate_options", "error", "Existen opciones repetidas.")
    if not isinstance(options, dict) or correct not in options:
        add("invalid_correct_key", "error", "La clave correcta no coincide con una opción disponible.")
    if len(rationale) < 25:
        add("weak_rationale", "error", "La justificación es insuficiente.")
    if not source:
        add("missing_source", "error", "Falta una fuente verificable.")
    elif not re.search(r"(art[ií]culo|decreto|ley|resoluci[oó]n|acuerdo|gu[ií]a|manual|anexo|cnsc|funci[oó]n)", source, re.I):
        add("vague_source", "warning", "La referencia existe, pero no identifica claramente una fuente oficial.")
    if difficulty not in (1, 2, 3):
        add("invalid_difficulty", "error", "La dificultad debe ser 1, 2 o 3.")
    if not str(getattr(question, "competency", "") or "").strip():
        add("missing_competency", "error", "Falta clasificar la competencia.")
    if not str(getattr(question, "topic", "") or "").strip():
        add("missing_topic", "error", "Falta clasificar el tema o función.")

    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    score = max(0, 100 - errors * 18 - warnings * 6)
    return {
        "version": "deterministic-v1",
        "status": "PASS" if not errors else "REVIEW",
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "findings": findings,
        "scope": "structure_and_traceability",
    }


def audit_bank(questions) -> dict:
    reports = {str(q.question_id): audit_question_structure(q) for q in questions}
    keys = Counter(str(getattr(q, "correct_key", "") or "").upper() for q in questions)
    total = len(reports)
    dominant_key, dominant_count = keys.most_common(1)[0] if keys else (None, 0)
    return {
        "total": total,
        "passed": sum(report["status"] == "PASS" for report in reports.values()),
        "review": sum(report["status"] == "REVIEW" for report in reports.values()),
        "dominant_key": dominant_key,
        "dominant_key_pct": round(dominant_count * 100 / total, 1) if total else 0.0,
        "reports": reports,
    }


def store_deterministic_audit(question, report: dict) -> None:
    current = dict(getattr(question, "quality_report", None) or {})
    current["deterministic_audit"] = report
    question.quality_report = current
