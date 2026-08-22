from __future__ import annotations

import re
import unicodedata
import math

from core.dedupe import compute_hash


def extract_candidates(payload, difficulty: int = 2, source_ref: str = "") -> list[dict]:
    """Normalize imported or model-generated JSON into review candidates."""
    if isinstance(payload, dict):
        raw = payload.get("questions")
        if raw is None and payload.get("stem"):
            raw = [payload]
    elif isinstance(payload, list):
        raw = payload
    else:
        raw = None
    if not isinstance(raw, list):
        return []

    candidates = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        stem = str(item.get("stem") or "").strip()
        options = item.get("options_json") or item.get("options")
        if not stem or not isinstance(options, dict):
            continue
        try:
            candidate_difficulty = int(item.get("difficulty") or difficulty)
        except (TypeError, ValueError):
            candidate_difficulty = int(difficulty)
        if not 1 <= candidate_difficulty <= 10:
            candidate_difficulty = min(max(int(difficulty), 1), 10)
        candidates.append({
            "track": str(item.get("track") or "FUNCIONAL").upper(),
            "macro_dominio": item.get("macro_dominio") or "Transversal",
            "micro_competencia": item.get("micro_competencia") or item.get("competency") or "General",
            "competency": item.get("competency") or item.get("micro_competencia") or "General",
            "topic": item.get("topic") or "Candidato generado",
            "difficulty": candidate_difficulty,
            "stem": stem,
            "options_json": options,
            "correct_key": str(item.get("correct_key") or "").upper(),
            "rationale": str(item.get("rationale") or "").strip(),
            "source_refs": str(item.get("source_refs") or item.get("source_ref") or source_ref).strip(),
            "hash_norm": item.get("hash_norm") or compute_hash(stem),
        })
    return candidates


def _terms(value: object) -> set[str]:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in normalized if not unicodedata.combining(char)).lower()
    stopwords = {"para", "como", "ante", "esta", "este", "debe", "puede", "sobre", "entre", "segun"}
    return {token for token in re.findall(r"[a-z0-9]+", text) if len(token) >= 4 and token not in stopwords}


def _normative_numbers(value: object) -> set[str]:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).lower()
    numbers = set(re.findall(r"\d+(?:-\d+)*", text))
    return {
        number
        for number in numbers
        if not (
            len(number) == 4
            and number.isdigit()
            and 1900 <= int(number) <= 2100
        )
    }


def candidate_issues(
    candidate: dict,
    source_text: str = "",
    *,
    require_source_text: bool = False,
) -> list[str]:
    issues = []
    options = candidate.get("options_json")
    if not str(candidate.get("stem") or "").strip():
        issues.append("Falta el enunciado")
    if not isinstance(options, dict) or tuple(options.keys()) != ("A", "B", "C"):
        issues.append("Debe tener exactamente las opciones A, B y C")
    elif candidate.get("correct_key") not in options:
        issues.append("La clave no corresponde a una opción")
    if not str(candidate.get("rationale") or "").strip():
        issues.append("Falta la justificación")
    if not str(candidate.get("source_refs") or "").strip():
        issues.append("Falta una fuente normativa identificable")
    if require_source_text and not source_text.strip():
        issues.append("Falta el texto fuente para verificar el sustento")
    elif source_text.strip():
        source_terms = _terms(source_text)

        content_text = " ".join(str(candidate.get(key) or "") for key in (
            "stem", "rationale", "micro_competencia"
        ))
        content_terms = _terms(content_text)
        semantic_overlap = len(source_terms & content_terms)

        topic_terms = _terms(candidate.get("topic"))
        topic_is_generic = (
            not topic_terms
            or topic_terms <= {"candidato", "generado", "general", "transversal"}
        )
        required_topic_overlap = max(1, math.ceil(len(topic_terms) * 0.4))
        topic_is_grounded = (
            topic_is_generic
            or len(source_terms & topic_terms) >= required_topic_overlap
        )

        source_numbers = _normative_numbers(source_text)
        reference_numbers = _normative_numbers(candidate.get("source_refs"))
        reference_matches = bool(source_numbers & reference_numbers)

        content_is_grounded = (
            semantic_overlap >= 2
            or (semantic_overlap >= 1 and reference_matches)
        )

        if not content_is_grounded or not topic_is_grounded:
            issues.append(
                "No se observa suficiente sustento en el texto proporcionado"
            )
    return issues
