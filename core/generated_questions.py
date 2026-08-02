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
        candidates.append({
            "track": str(item.get("track") or "FUNCIONAL").upper(),
            "macro_dominio": item.get("macro_dominio") or "Transversal",
            "micro_competencia": item.get("micro_competencia") or item.get("competency") or "General",
            "competency": item.get("competency") or item.get("micro_competencia") or "General",
            "topic": item.get("topic") or "Candidato generado",
            "difficulty": int(item.get("difficulty") or difficulty),
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


def candidate_issues(candidate: dict, source_text: str = "") -> list[str]:
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
    if source_text.strip():
        source_terms = _terms(source_text)
        candidate_text = " ".join(str(candidate.get(key) or "") for key in (
            "topic", "stem", "rationale", "micro_competencia"
        ))
        topic_terms = _terms(candidate.get("topic"))
        required_topic_overlap = max(1, math.ceil(len(topic_terms) * 0.4))
        topic_is_grounded = not topic_terms or len(source_terms & topic_terms) >= required_topic_overlap
        if len(source_terms & _terms(candidate_text)) < 2 or not topic_is_grounded:
            issues.append("No se observa suficiente sustento en el texto proporcionado")
    return issues
