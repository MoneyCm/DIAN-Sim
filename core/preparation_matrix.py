"""Evidence-based preparation matrix for a configured OPEC.

The static blueprint records what should be covered. Live question and user
performance data records what is actually covered. Provisional planning targets
must never be interpreted as official exam weights.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.exam_format import has_source_grounded_review
from core.opec_question_context import function_number_for_question
from core.source_evidence import has_precise_source_verification


BLUEPRINT_PATH = Path(__file__).resolve().parents[1] / "data" / "opec_236769_matrix.json"
SOURCE_READY_STATES = {"official_available", "official_verified"}


def load_preparation_blueprint(opec_number: object) -> dict:
    """Load the versioned blueprint only for the OPEC it declares."""
    try:
        payload = json.loads(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if str(payload.get("opec_number", "")) != str(opec_number or "").strip():
        return {}
    payload["functions"] = sorted(
        payload.get("functions", []), key=lambda item: int(item.get("number", 0) or 0)
    )
    return payload


def _performance_totals(performance) -> tuple[int, int, float]:
    if performance is None:
        return 0, 0, 0.0
    hits = int(getattr(performance, "hits", 0) or 0)
    misses = int(getattr(performance, "misses", 0) or 0)
    if hits + misses <= 0:
        return hits, misses, 0.0

    # QuestionPerformance.mastery_level is canonically stored on a 0-10
    # scale.  The preparation matrix exposes a 0-1 ratio because its UI
    # consumers render the value as a percentage.  Do not reinterpret legacy
    # fractional values (for example, 0.8) as 80% without an explicit data
    # migration: on the canonical scale that value represents 8%.
    mastery_0_to_10 = float(
        getattr(performance, "mastery_level", 0.0) or 0.0
    )
    mastery_ratio = mastery_0_to_10 / 10.0
    return hits, misses, max(0.0, min(mastery_ratio, 1.0))


def _coverage_state(trusted: int, target: int, source_ready: bool) -> str:
    if not source_ready:
        return "Fuente pendiente"
    ratio = trusted / max(target, 1)
    if ratio < 0.15:
        return "Brecha crítica"
    if ratio < 0.50:
        return "Cobertura en desarrollo"
    if ratio < 1.0:
        return "Cobertura avanzada"
    return "Meta provisional cubierta"


def _risk_level(*, coverage_ratio: float, source_ready: bool, attempts: int, mastery: float) -> str:
    if not source_ready or coverage_ratio < 0.15 or attempts < 3:
        return "Alto"
    if coverage_ratio < 0.60 or mastery < 0.75 or attempts < 12:
        return "Medio"
    return "Bajo"


def _next_action(*, source_ready: bool, trusted: int, target: int, attempts: int, mastery: float) -> str:
    if not source_ready:
        return "Confirmar y versionar la fuente oficial antes de ampliar este bloque."
    if trusted < target:
        return f"Ampliar el banco con {target - trusted} pregunta(s) revisada(s), en lotes pequeños y trazables."
    if attempts < 6:
        return "Aplicar un diagnóstico con preguntas nuevas de esta función."
    if mastery < 0.85:
        return "Estudiar la fuente prioritaria y reforzar errores con preguntas nuevas."
    return "Mantener dominio con transferencia, presión de tiempo y repaso espaciado."


def build_master_preparation_matrix(
    opec_number: object,
    functions,
    questions,
    performances,
) -> dict:
    """Combine the OPEC blueprint with live bank and user-performance evidence."""
    blueprint = load_preparation_blueprint(opec_number)
    if not blueprint:
        return {"available": False, "rows": [], "unmatched_questions": len(list(questions or []))}

    function_texts = [str(item).strip() for item in (functions or []) if str(item).strip()]
    source_by_id = {item["id"]: item for item in blueprint.get("sources", [])}
    performance_by_question = {
        str(getattr(item, "question_id", "")): item for item in (performances or [])
    }
    buckets = {
        int(item["number"]): {"questions": [], "case_ids": set()}
        for item in blueprint.get("functions", [])
    }
    unmatched = 0

    for question in questions or []:
        number = function_number_for_question(question, str(opec_number or ""))
        if number not in buckets:
            unmatched += 1
            continue
        buckets[number]["questions"].append(question)
        case = getattr(question, "case_study", None)
        case_id = getattr(case, "id", None) or getattr(question, "case_id", None)
        if case_id:
            buckets[number]["case_ids"].add(str(case_id))

    rows = []
    total_trusted = 0
    total_target = 0
    for definition in blueprint.get("functions", []):
        number = int(definition["number"])
        bucket_questions = buckets[number]["questions"]
        trusted = sum(
            bool(getattr(question, "is_verified", False))
            and has_source_grounded_review(question)
            and has_precise_source_verification(question)
            for question in bucket_questions
        )
        hits = misses = 0
        mastery_values = []
        exposed_questions = 0
        for question in bucket_questions:
            performance = performance_by_question.get(str(getattr(question, "question_id", "")))
            q_hits, q_misses, mastery = _performance_totals(performance)
            hits += q_hits
            misses += q_misses
            if q_hits + q_misses:
                exposed_questions += 1
                mastery_values.append(mastery)

        attempts = hits + misses
        mastery = sum(mastery_values) / len(mastery_values) if mastery_values else 0.0
        accuracy = hits / attempts if attempts else 0.0
        target = int(definition.get("functional_question_target", 0) or 0)
        coverage_ratio = min(trusted / max(target, 1), 1.0)
        sources = [
            source_by_id[source_id]
            for source_id in definition.get("source_ids", [])
            if source_id in source_by_id
        ]
        missing_source_ids = [
            source_id for source_id in definition.get("source_ids", [])
            if source_id not in source_by_id
        ]
        source_ready = bool(sources) and not missing_source_ids and all(
            source.get("status") in SOURCE_READY_STATES for source in sources
        )
        function_text = definition.get("official_function_text", "") or definition.get("function", "") or (
            function_texts[number - 1] if number <= len(function_texts) else ""
        )
        rows.append({
            **definition,
            "function": function_text,
            "question_count": len(bucket_questions),
            "trusted_question_count": trusted,
            "case_count": len(buckets[number]["case_ids"]),
            "exposed_question_count": exposed_questions,
            "attempt_count": attempts,
            "accuracy": accuracy,
            "mastery": mastery,
            "coverage_ratio": coverage_ratio,
            "coverage_status": _coverage_state(trusted, target, source_ready),
            "risk": _risk_level(
                coverage_ratio=coverage_ratio,
                source_ready=source_ready,
                attempts=attempts,
                mastery=mastery,
            ),
            "source_ready": source_ready,
            "sources": sources,
            "missing_source_ids": missing_source_ids,
            "next_action": _next_action(
                source_ready=source_ready,
                trusted=trusted,
                target=target,
                attempts=attempts,
                mastery=mastery,
            ),
        })
        total_trusted += trusted
        total_target += target

    return {
        "available": True,
        "opec_number": str(opec_number),
        "version": blueprint.get("version"),
        "reviewed_on": blueprint.get("reviewed_on"),
        "exam_format_status": blueprint.get("exam_format_status"),
        "target_score": blueprint.get("target_score", 85),
        "bank_targets": blueprint.get("bank_targets", {}),
        "rows": rows,
        "source_registry": blueprint.get("sources", []),
        "trusted_question_count": total_trusted,
        "functional_question_target": total_target,
        "coverage_ratio": min(total_trusted / max(total_target, 1), 1.0),
        "high_risk_functions": sum(row["risk"] == "Alto" for row in rows),
        "unmatched_questions": unmatched,
    }
