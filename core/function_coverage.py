from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from core.exam_format import has_source_grounded_review


_MATRIX_CACHE: dict[str, dict[int, str]] = {}


def _load_short_names(opec_number: str) -> dict[int, str]:
    if opec_number in _MATRIX_CACHE:
        return _MATRIX_CACHE[opec_number]
    mapping: dict[int, str] = {}
    base = Path(__file__).resolve().parents[1] / "data"
    # Try dedicated matrix file first (e.g. opec_236769_matrix.json)
    matrix_path = base / f"opec_{opec_number}_matrix.json"
    if not matrix_path.exists():
        matrix_path = base / "opec_236769_matrix.json"
    try:
        with open(matrix_path, encoding="utf-8") as f:
            data = json.load(f)
        for fn in data.get("functions", []):
            if "number" in fn and "short_name" in fn:
                mapping[int(fn["number"])] = fn["short_name"]
    except Exception:
        pass
    _MATRIX_CACHE[opec_number] = mapping
    return mapping


def function_display_label(opec_number: str, number: int, full_text: str = "") -> str:
    """Standardized 'F6 · Short name' label for all UI locations."""
    short_names = _load_short_names(opec_number)
    short = short_names.get(number, "")
    if not short:
        compact = " ".join(str(full_text or "").split())
        short = compact[:80].rstrip() + ("..." if len(compact) > 80 else "")
    return f"F{number} \u00b7 {short}"


def function_display_detail(opec_number: str, number: int, full_text: str = "") -> str:
    """Standardized 'F6 · Short name\\nFull MERF text' for expanders."""
    label = function_display_label(opec_number, number, full_text)
    if full_text and full_text != label:
        return f"{label}\n{full_text}"
    return label


MIN_QUESTIONS_PER_FUNCTION = 5
MIN_ATTEMPTS_FOR_PRACTICE = 3
MIN_SHARED_TERMS = 3
EXPLICIT_OPEC_FUNCTION = re.compile(r"\bOPEC\s+236769\s+F([1-9])\b", re.I)

STOPWORDS = {
    "acuerdo", "asignadas", "autoridad", "cargo", "competencia", "cumplimiento",
    "directrices", "entidad", "establecidos", "funcion", "funciones", "jurisdiccion",
    "lineamientos", "marco", "materia", "nivel", "normativa", "pertinente", "proceso",
    "procedimiento", "procedimientos", "realizar", "requeridos", "responsabilidad",
    "señaladas", "vigente", "para", "como", "dentro", "sobre", "entre", "desde",
    "esta", "este", "estas", "estos", "segun", "cada", "otras", "otros", "propios",
}


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def _terms(value: object) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", _normalize(value))
        if len(token) >= 5 and token not in STOPWORDS
    }


def _question_text(question) -> str:
    return " ".join(str(value or "") for value in (
        getattr(question, "macro_dominio", None),
        getattr(question, "micro_competencia", None),
        getattr(question, "competency", None),
        getattr(question, "topic", None),
        getattr(question, "stem", None),
        getattr(question, "rationale", None),
        getattr(question, "source_refs", None),
    ))


def function_label(function: str, number: int, max_length: int = 90, opec_number: str = "") -> str:
    if opec_number:
        return function_display_label(opec_number, number, function)
    compact = " ".join(str(function or "").split())
    if len(compact) > max_length:
        compact = compact[:max_length - 1].rstrip() + "\u2026"
    return f"F{number}. {compact}"


def build_function_coverage(functions, questions, performances) -> tuple[list[dict], int]:
    """Map questions conservatively to the best matching OPEC function."""
    clean_functions = [str(item).strip() for item in (functions or []) if str(item).strip()]
    function_terms = [_terms(item) for item in clean_functions]
    performance_by_question = {item.question_id: item for item in performances}
    buckets = [{"questions": 0, "trusted": 0, "practiced": 0, "shared": []}
               for _ in clean_functions]
    unmatched = 0

    for question in questions:
        explicit_match = EXPLICIT_OPEC_FUNCTION.search(
            str(getattr(question, "micro_competencia", "") or "")
        )
        if explicit_match:
            index = int(explicit_match.group(1)) - 1
            if index < len(buckets):
                bucket = buckets[index]
                bucket["questions"] += 1
                bucket["shared"].append(MIN_SHARED_TERMS)
                if bool(getattr(question, "is_verified", False)) and has_source_grounded_review(question):
                    bucket["trusted"] += 1
                performance = performance_by_question.get(question.question_id)
                attempts = int(performance.hits or 0) + int(performance.misses or 0) if performance else 0
                if attempts >= MIN_ATTEMPTS_FOR_PRACTICE:
                    bucket["practiced"] += 1
                continue
        q_terms = _terms(_question_text(question))
        candidates = []
        for index, terms in enumerate(function_terms):
            shared = terms & q_terms
            score = len(shared) / max(1, min(len(terms), 10))
            candidates.append((score, len(shared), index, shared))
        best = max(candidates, default=(0, 0, -1, set()))
        if best[1] < MIN_SHARED_TERMS:
            unmatched += 1
            continue
        _, _, index, shared = best
        bucket = buckets[index]
        bucket["questions"] += 1
        bucket["shared"].append(len(shared))
        if bool(getattr(question, "is_verified", False)) and has_source_grounded_review(question):
            bucket["trusted"] += 1
        performance = performance_by_question.get(question.question_id)
        attempts = int(performance.hits or 0) + int(performance.misses or 0) if performance else 0
        if attempts >= MIN_ATTEMPTS_FOR_PRACTICE:
            bucket["practiced"] += 1

    rows = []
    for index, (function, bucket) in enumerate(zip(clean_functions, buckets), start=1):
        if bucket["questions"] < MIN_QUESTIONS_PER_FUNCTION:
            status = "Faltan preguntas"
        elif bucket["trusted"] == 0:
            status = "Revisar calidad"
        elif bucket["practiced"] == 0:
            status = "Pendiente de práctica"
        else:
            status = "Con evidencia"
        rows.append({
            "function_number": index,
            "function": function,
            "label": function_label(function, index),
            "questions": bucket["questions"],
            "trusted": bucket["trusted"],
            "practiced": bucket["practiced"],
            "status": status,
        })
    return rows, unmatched


def build_function_study_map(functions, questions, performances, catalog_sources=None) -> tuple[list[dict], int]:
    """Return one practical study recommendation and verified sources per OPEC function."""
    coverage_rows, unmatched = build_function_coverage(functions, questions, performances)
    clean_functions = [str(item).strip() for item in (functions or []) if str(item).strip()]
    function_terms = [_terms(item) for item in clean_functions]
    sources_by_function = [[] for _ in clean_functions]

    for question in questions:
        q_terms = _terms(_question_text(question))
        candidates = []
        for index, terms in enumerate(function_terms):
            shared = terms & q_terms
            candidates.append((len(shared), index))
        shared_count, index = max(candidates, default=(0, -1))
        source = " ".join(str(getattr(question, "source_refs", "") or "").split())
        if (
            index >= 0
            and shared_count >= MIN_SHARED_TERMS
            and source
            and bool(getattr(question, "is_verified", False))
            and has_source_grounded_review(question)
            and source not in sources_by_function[index]
        ):
            sources_by_function[index].append(source)

    study_rows = []
    for index, row in enumerate(coverage_rows):
        status = row["status"]
        if status == "Faltan preguntas":
            recommendation = "Falta banco: cargar fuente oficial y crear al menos 5 preguntas verificadas."
        elif status == "Revisar calidad":
            recommendation = "Verificar fuente, vigencia, clave y distractores antes de usar el tema."
        elif status == "Pendiente de práctica":
            recommendation = "Estudia la fuente vinculada y responde al menos 3 preguntas del tema."
        else:
            recommendation = "Mantén el tema con repaso espaciado y casos situacionales nuevos."
        catalogue = (catalog_sources or {}).get(index + 1, [])
        combined_sources = list(dict.fromkeys(sources_by_function[index] + list(catalogue)))
        study_rows.append({
            **row,
            "sources": combined_sources[:4],
            "recommendation": recommendation,
        })
    return study_rows, unmatched
