"""Deterministic, free quality checks for question-bank candidates."""

from __future__ import annotations

import re
from collections import Counter

from rapidfuzz import fuzz

from core.dedupe import normalize_text
from core.learning.engine import editorial_question_difficulty


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
    question_type = str(getattr(question, "question_type", "") or "").strip().upper()
    track = str(getattr(question, "track", "") or "").strip().upper()
    is_likert = question_type == "LIKERT" or track in {"COMPORTAMENTAL", "INTEGRIDAD"}
    difficulty = editorial_question_difficulty(question)

    minimum_stem_length = 15 if is_likert else 35
    if len(stem) < minimum_stem_length:
        add("stem_too_short", "error", "El enunciado es demasiado corto para aportar contexto suficiente.")
    expected_option_count = 4 if is_likert else 3
    if not isinstance(options, dict) or len(options) != expected_option_count:
        add(
            "invalid_options",
            "error",
            "La afirmación Likert debe tener exactamente cuatro opciones."
            if is_likert
            else "La pregunta debe tener exactamente tres opciones.",
        )
        option_values = []
    else:
        expected = {"A", "B", "C", "D"} if is_likert else {"A", "B", "C"}
        if set(options) != expected:
            add(
                "invalid_option_keys",
                "error",
                "Las opciones deben identificarse como A, B, C y D."
                if is_likert
                else "Las opciones deben identificarse como A, B y C.",
            )
        option_values = [re.sub(r"\s+", " ", str(value or "").strip().lower()) for value in options.values()]
        if any(not value for value in option_values):
            add("empty_option", "error", "Hay una opción vacía.")
        if len(set(option_values)) != len(option_values):
            add("duplicate_options", "error", "Existen opciones repetidas.")
        option_lengths = [len(value) for value in option_values if value]
        if option_lengths and min(option_lengths) > 0:
            if max(option_lengths) / min(option_lengths) > 2.5:
                add(
                    "uneven_option_lengths",
                    "warning",
                    "Las opciones tienen longitudes muy desiguales y pueden dar una pista.",
                )
        if not is_likert and isinstance(options, dict) and correct in options:
            correct_length = len(str(options[correct] or "").strip())
            other_lengths = [
                len(str(value or "").strip())
                for key, value in options.items()
                if key != correct
            ]
            if other_lengths and correct_length > max(other_lengths) * 1.8:
                add(
                    "correct_option_length_hint",
                    "warning",
                    "La opción correcta es desproporcionadamente más larga que los distractores.",
                )
    if is_likert and correct:
        add("likert_has_key", "error", "Una afirmación Likert no debe tener clave correcta.")
    elif not is_likert and (not isinstance(options, dict) or correct not in options):
        add("invalid_correct_key", "error", "La clave correcta no coincide con una opción disponible.")
    if len(rationale) < 25:
        add("weak_rationale", "error", "La justificación es insuficiente.")
    if not source:
        add("missing_source", "error", "Falta una fuente verificable.")
    elif not re.search(r"(art[ií]culo|decreto|ley|resoluci[oó]n|acuerdo|gu[ií]a|manual|anexo|cnsc|funci[oó]n)", source, re.I):
        add("vague_source", "warning", "La referencia existe, pero no identifica claramente una fuente oficial.")
    if not 1 <= difficulty <= 10:
        add("invalid_difficulty", "error", "La dificultad editorial debe estar entre 1 y 10.")
    if not str(getattr(question, "competency", "") or "").strip():
        add("missing_competency", "error", "Falta clasificar la competencia.")
    if not str(getattr(question, "topic", "") or "").strip():
        add("missing_topic", "error", "Falta clasificar el tema o función.")
    negative_tokens = re.findall(r"\b(?:no|nunca|excepto|incorrecta)\b", stem, re.I)
    if len(negative_tokens) > 1:
        add(
            "confusing_negation",
            "warning",
            "El enunciado acumula negaciones y puede medir lectura confusa en vez de criterio.",
        )

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


def find_near_duplicate_pairs(
    questions,
    *,
    threshold: int = 92,
    max_pairs: int = 100,
) -> list[dict]:
    """Return deterministic paraphrase candidates without mutating the bank."""

    prepared = [
        (
            str(getattr(question, "question_id", "") or ""),
            normalize_text(str(getattr(question, "stem", "") or "")),
        )
        for question in questions or ()
    ]
    pairs = []
    for index, (left_id, left_text) in enumerate(prepared):
        if not left_text:
            continue
        for right_id, right_text in prepared[index + 1:]:
            if not right_text:
                continue
            score = round(float(fuzz.token_set_ratio(left_text, right_text)), 1)
            if score >= int(threshold):
                pairs.append({
                    "question_id": left_id,
                    "duplicate_question_id": right_id,
                    "similarity": score,
                })
                if len(pairs) >= int(max_pairs):
                    return pairs
    return pairs


def audit_bank(questions) -> dict:
    questions = list(questions or ())
    reports = {str(q.question_id): audit_question_structure(q) for q in questions}
    keys = Counter(
        key
        for q in questions
        if (key := str(getattr(q, "correct_key", "") or "").upper())
    )
    total = len(reports)
    dominant_key, dominant_count = keys.most_common(1)[0] if keys else (None, 0)
    duplicate_pairs = find_near_duplicate_pairs(questions)
    return {
        "total": total,
        "passed": sum(report["status"] == "PASS" for report in reports.values()),
        "review": sum(report["status"] == "REVIEW" for report in reports.values()),
        "dominant_key": dominant_key,
        "dominant_key_pct": round(dominant_count * 100 / total, 1) if total else 0.0,
        "near_duplicate_count": len(duplicate_pairs),
        "near_duplicate_pairs": duplicate_pairs,
        "reports": reports,
    }


def store_deterministic_audit(question, report: dict) -> None:
    current = dict(getattr(question, "quality_report", None) or {})
    current["deterministic_audit"] = report
    question.quality_report = current
