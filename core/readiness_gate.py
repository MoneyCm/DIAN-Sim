"""Transparent internal readiness gates for structured practice history.

This module deliberately does not calculate an official CNSC result.  It
evaluates whether a user has repeated a configurable *internal* accuracy goal
under comparable measurement conditions.  All inputs are plain dataclasses or
mappings so the policy can be tested without a database or Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Mapping, Sequence


INTERNAL_CLAIM_STATUS = "internal_diagnostic_not_official_result"
PRECISION_TARGET_LABEL = "objetivo interno de precisión"
OFFICIAL_MINIMUM_LABEL = "mínimo oficial funcional"
OFFICIAL_FUNCTIONAL_MINIMUM_SCORE = 70.0


@dataclass(frozen=True)
class ReadinessPolicy:
    """Editable internal policy; none of these values are CNSC rules."""

    version: str = "internal-readiness-v1"
    target_score: float = 85.0
    required_sessions: int = 3
    minimum_functional_items_per_session: int = 30
    required_function_numbers: tuple[int, ...] = tuple(range(1, 10))
    max_session_age_days: int = 30
    minimum_retention_delay_days: int = 7
    minimum_retention_functional_items: int = 9
    retention_target_score: float | None = None

    def __post_init__(self) -> None:
        if not str(self.version).strip():
            raise ValueError("La política interna debe tener versión")
        if not 0.0 <= float(self.target_score) <= 100.0:
            raise ValueError("La meta interna debe estar entre 0 y 100")
        if int(self.required_sessions) < 1:
            raise ValueError("Se requiere al menos una sesión")
        if int(self.minimum_functional_items_per_session) < 1:
            raise ValueError("El mínimo funcional por sesión debe ser positivo")
        if not self.required_function_numbers:
            raise ValueError("La cobertura debe incluir al menos una función")
        if int(self.max_session_age_days) < 0:
            raise ValueError("La ventana de actualidad no puede ser negativa")
        if int(self.minimum_retention_delay_days) < 0:
            raise ValueError("La demora de retención no puede ser negativa")
        if int(self.minimum_retention_functional_items) < 1:
            raise ValueError("El mínimo de retención debe ser positivo")
        retention_target = (
            self.target_score
            if self.retention_target_score is None
            else self.retention_target_score
        )
        if not 0.0 <= float(retention_target) <= 100.0:
            raise ValueError("La meta de retención debe estar entre 0 y 100")


@dataclass(frozen=True)
class BankEvidence:
    """Evidence supplied by the source and bank-quality subsystem."""

    sources_verified: bool
    measurement_bank_trusted: bool
    trusted_revision_ids: frozenset[str] | None = None
    note: str = ""


@dataclass(frozen=True)
class ItemResult:
    revision_id: str
    case_id: str
    function_number: int | None
    is_correct: bool | None
    track: str = "FUNCIONAL"
    question_type: str = "SITUATIONAL"


@dataclass(frozen=True)
class MeasurementSessionResult:
    session_id: str
    user_id: object
    competition_id: object
    opec_number: object
    policy_version: str
    blueprint_version: str
    completed_at: datetime | str | None
    items: tuple[ItemResult | Mapping[str, Any], ...]
    started_at: datetime | str | None = None
    bank_partition: str = "measurement"
    completed: bool = True
    feedback_enabled: bool = False
    aids_used: bool = False
    # Compatibility for structured historical summaries that did not retain
    # correctness per item.  It must already be functional-only.  When item
    # correctness exists, the score is recomputed and this value is audited.
    functional_score: float | None = None


@dataclass(frozen=True)
class RetentionEvidence:
    retention_id: str
    user_id: object
    competition_id: object
    opec_number: object
    policy_version: str
    blueprint_version: str
    anchor_at: datetime | str
    measured_at: datetime | str
    items: tuple[ItemResult | Mapping[str, Any], ...]
    completed: bool = True
    feedback_enabled: bool = False
    aids_used: bool = False
    functional_score: float | None = None


@dataclass(frozen=True)
class GateResult:
    key: str
    status: str
    met: bool
    reasons: tuple[str, ...] = ()
    evidence: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadinessAssessment:
    """Internal evidence report, intentionally not an official pass/fail."""

    status: str
    claim_status: str
    precision_target_label: str
    repeated_target_label: str
    target_score: float
    official_functional_minimum_label: str
    official_functional_minimum_score: float
    official_result: None
    internal_precision_goal_met: bool
    internal_retention_goal_met: bool | None
    selected_session_ids: tuple[str, ...]
    session_scores: tuple[float | None, ...]
    gates: tuple[GateResult, ...]
    retention_gate: GateResult
    reasons: tuple[str, ...]

    def gate(self, key: str) -> GateResult:
        """Return a named measurement gate for callers and tests."""
        for gate in self.gates:
            if gate.key == key:
                return gate
        raise KeyError(key)


_MISSING = object()


def _value(record: object, name: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(name, default)
    return getattr(record, name, default)


def _identity(value: object) -> str:
    return "" if value is None else str(value).strip()


def _utc_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _session_id(session: object, index: int) -> str:
    return _identity(_value(session, "session_id")) or f"session-{index + 1}"


def _session_time(session: object) -> datetime:
    parsed = _utc_datetime(_value(session, "completed_at"))
    parsed = parsed or _utc_datetime(_value(session, "started_at"))
    return parsed or datetime.min.replace(tzinfo=timezone.utc)


def _items(record: object) -> tuple[object, ...]:
    raw = _value(record, "items", ())
    if raw is None or isinstance(raw, (str, bytes, Mapping)):
        return ()
    try:
        return tuple(raw)
    except TypeError:
        return ()


def _is_functional_scored(item: object) -> bool:
    track = _identity(_value(item, "track")).upper()
    question_type = _identity(_value(item, "question_type")).upper()
    return track == "FUNCIONAL" and question_type not in {
        "LIKERT",
        "SELF_REPORT",
        "AUTORREPORTE",
    }


def _functional_items(record: object) -> tuple[object, ...]:
    return tuple(item for item in _items(record) if _is_functional_scored(item))


def _numeric_score(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if 0.0 <= score <= 100.0 else None


def _functional_metrics(record: object) -> dict[str, Any]:
    functional_items = _functional_items(record)
    total = len(functional_items)
    correctness = [_value(item, "is_correct", _MISSING) for item in functional_items]
    provided_score = _numeric_score(_value(record, "functional_score"))
    errors: list[str] = []

    all_known = bool(correctness) and all(isinstance(value, bool) for value in correctness)
    all_unknown = bool(correctness) and all(
        value is None or value is _MISSING for value in correctness
    )
    if all_known:
        correct = sum(value is True for value in correctness)
        score = correct / total * 100.0
        origin = "recomputed_from_functional_items"
        if provided_score is not None and abs(provided_score - score) > 0.01:
            errors.append(
                "El puntaje funcional informado no coincide con los ítems funcionales."
            )
    elif all_unknown and provided_score is not None:
        correct = None
        score = provided_score
        origin = "provided_functional_summary"
    else:
        correct = None
        score = None
        origin = "unavailable"
        if total == 0:
            errors.append("La sesión no contiene ítems funcionales puntuables.")
        elif any(isinstance(value, bool) for value in correctness):
            errors.append("La corrección funcional está incompleta.")
        else:
            errors.append("Falta el puntaje funcional de la sesión histórica.")

    return {
        "items": functional_items,
        "total": total,
        "correct": correct,
        "score": score,
        "score_origin": origin,
        "errors": tuple(errors),
    }


def _gate(
    key: str,
    met: bool,
    reasons: Sequence[str] = (),
    **evidence: Any,
) -> GateResult:
    return GateResult(
        key=key,
        status="met" if met else "not_met",
        met=met,
        reasons=tuple(reasons),
        evidence=evidence,
    )


def _context(record: object) -> tuple[str, str, str, str, str]:
    return (
        _identity(_value(record, "user_id")),
        _identity(_value(record, "competition_id")),
        _identity(_value(record, "opec_number")),
        _identity(_value(record, "policy_version")),
        _identity(_value(record, "blueprint_version")),
    )


def _evaluate_retention(
    retention: object | None,
    *,
    policy: ReadinessPolicy,
    expected_context: tuple[str, str, str, str, str] | None,
    bank_evidence: BankEvidence | Mapping[str, Any] | None,
    as_of: datetime,
) -> GateResult:
    if retention is None:
        return GateResult(
            key="delayed_retention",
            status="pending",
            met=False,
            reasons=("La comprobación de retención diferida sigue pendiente.",),
            evidence={
                "minimum_delay_days": policy.minimum_retention_delay_days,
                "claim_status": INTERNAL_CLAIM_STATUS,
            },
        )

    reasons: list[str] = []
    if _value(retention, "completed") is not True:
        reasons.append("La comprobación de retención no está completa.")
    if _value(retention, "feedback_enabled") is not False:
        reasons.append("La comprobación de retención tuvo retroalimentación habilitada.")
    if _value(retention, "aids_used") is not False:
        reasons.append("La comprobación de retención registró ayudas.")

    retention_context = _context(retention)
    if expected_context is None or retention_context != expected_context:
        reasons.append("La retención no pertenece al mismo contexto versionado de medición.")

    anchor_at = _utc_datetime(_value(retention, "anchor_at"))
    measured_at = _utc_datetime(_value(retention, "measured_at"))
    delay_days: float | None = None
    if anchor_at is None or measured_at is None:
        reasons.append("La retención no tiene fechas válidas de anclaje y medición.")
    else:
        delay_days = (measured_at - anchor_at).total_seconds() / 86400.0
        if delay_days < policy.minimum_retention_delay_days:
            reasons.append(
                "La retención se midió antes de la demora interna configurada."
            )
        if measured_at > as_of:
            reasons.append("La fecha de retención está en el futuro.")

    metrics = _functional_metrics(retention)
    reasons.extend(metrics["errors"])
    if metrics["total"] < policy.minimum_retention_functional_items:
        reasons.append(
            "La retención no alcanza el mínimo interno de ítems funcionales."
        )
    retention_target = float(
        policy.target_score
        if policy.retention_target_score is None
        else policy.retention_target_score
    )
    if metrics["score"] is None or metrics["score"] < retention_target:
        reasons.append("La retención no alcanza el objetivo interno configurado.")

    trusted_ids_raw = (
        _value(bank_evidence, "trusted_revision_ids")
        if bank_evidence is not None
        else None
    )
    if trusted_ids_raw is not None:
        trusted_ids = {_identity(value) for value in trusted_ids_raw}
        retention_ids = {
            _identity(_value(item, "revision_id")) for item in metrics["items"]
        }
        if "" in retention_ids or not retention_ids.issubset(trusted_ids):
            reasons.append("La retención contiene revisiones sin evidencia confiable.")

    return _gate(
        "delayed_retention",
        not reasons,
        reasons,
        retention_id=_identity(_value(retention, "retention_id")),
        delay_days=delay_days,
        functional_total=metrics["total"],
        functional_score=metrics["score"],
        target_score=retention_target,
        claim_status=INTERNAL_CLAIM_STATUS,
    )


def evaluate_readiness(
    sessions: Sequence[MeasurementSessionResult | Mapping[str, Any]],
    *,
    bank_evidence: BankEvidence | Mapping[str, Any] | None,
    policy: ReadinessPolicy | None = None,
    retention: RetentionEvidence | Mapping[str, Any] | None = None,
    as_of: datetime | str | None = None,
) -> ReadinessAssessment:
    """Evaluate internal readiness without inferring an official outcome.

    When more sessions than required are supplied, the newest configured
    number is evaluated.  Callers should therefore pass the history for the
    intended user/OPEC; mixed contexts in the selected window fail closed.
    """

    policy = policy or ReadinessPolicy()
    evaluated_at = _utc_datetime(as_of) if as_of is not None else datetime.now(timezone.utc)
    if evaluated_at is None:
        raise ValueError("La fecha de evaluación no es válida")

    history = list(sessions or ())
    indexed = list(enumerate(history))
    indexed.sort(key=lambda pair: (_session_time(pair[1]), pair[0]), reverse=True)
    selected_pairs = indexed[: policy.required_sessions]
    selected = [session for _, session in selected_pairs]
    selected_ids = tuple(
        _session_id(session, original_index) for original_index, session in selected_pairs
    )

    count_gate = _gate(
        "measurement_session_count",
        len(selected) == policy.required_sessions,
        () if len(selected) == policy.required_sessions else (
            f"Se requieren al menos {policy.required_sessions} sesiones de medición; "
            f"solo hay {len(selected)}.",
        ),
        required=policy.required_sessions,
        available=len(history),
        evaluated=len(selected),
    )

    wrong_partitions = [
        selected_ids[index]
        for index, session in enumerate(selected)
        if _identity(_value(session, "bank_partition")).lower() != "measurement"
    ]
    partition_gate = _gate(
        "measurement_partition",
        not wrong_partitions and bool(selected),
        () if not wrong_partitions and selected else (
            "Todas las sesiones evaluadas deben pertenecer a la partición measurement.",
        ),
        invalid_session_ids=tuple(wrong_partitions),
    )

    incomplete = [
        selected_ids[index]
        for index, session in enumerate(selected)
        if _value(session, "completed") is not True
    ]
    completion_gate = _gate(
        "completed_sessions",
        not incomplete and bool(selected),
        () if not incomplete and selected else (
            "Todas las sesiones de medición deben estar completas.",
        ),
        incomplete_session_ids=tuple(incomplete),
    )

    assisted = [
        selected_ids[index]
        for index, session in enumerate(selected)
        if _value(session, "feedback_enabled") is not False
        or _value(session, "aids_used") is not False
    ]
    assistance_gate = _gate(
        "no_feedback_or_aids",
        not assisted and bool(selected),
        () if not assisted and selected else (
            "Las sesiones de medición deben realizarse sin retroalimentación ni ayudas.",
        ),
        assisted_session_ids=tuple(assisted),
    )

    contexts = [_context(session) for session in selected]
    context_complete = bool(contexts) and all(all(parts) for parts in contexts)
    same_context = context_complete and len(set(contexts)) == 1
    policy_matches = same_context and contexts[0][3] == policy.version
    context_reasons: list[str] = []
    if not context_complete:
        context_reasons.append("Falta identidad o versión en una sesión de medición.")
    elif not same_context:
        context_reasons.append(
            "Las sesiones mezclan usuario, concurso, OPEC, política o blueprint."
        )
    elif not policy_matches:
        context_reasons.append(
            "La versión registrada por las sesiones no coincide con la política evaluada."
        )
    context_gate = _gate(
        "same_versioned_context",
        same_context and policy_matches,
        context_reasons,
        context=contexts[0] if same_context else None,
        policy_version=policy.version,
    )
    expected_context = contexts[0] if same_context and policy_matches else None

    cutoff = evaluated_at - timedelta(days=policy.max_session_age_days)
    stale_or_invalid: list[str] = []
    completed_times: list[datetime | None] = []
    for index, session in enumerate(selected):
        completed_at = _utc_datetime(_value(session, "completed_at"))
        completed_times.append(completed_at)
        if completed_at is None or completed_at < cutoff or completed_at > evaluated_at:
            stale_or_invalid.append(selected_ids[index])
    recency_gate = _gate(
        "recent_sessions",
        not stale_or_invalid and bool(selected),
        () if not stale_or_invalid and selected else (
            "Todas las sesiones deben estar dentro de la ventana interna de actualidad.",
        ),
        max_age_days=policy.max_session_age_days,
        invalid_session_ids=tuple(stale_or_invalid),
    )

    metrics = [_functional_metrics(session) for session in selected]
    totals_reasons: list[str] = []
    for index, metric in enumerate(metrics):
        if metric["total"] < policy.minimum_functional_items_per_session:
            totals_reasons.append(
                f"{selected_ids[index]} tiene {metric['total']} ítems funcionales; "
                f"se requieren {policy.minimum_functional_items_per_session}."
            )
    totals_gate = _gate(
        "minimum_functional_total",
        not totals_reasons and len(metrics) == policy.required_sessions,
        totals_reasons or (() if len(metrics) == policy.required_sessions else (
            "No hay suficientes sesiones para comprobar el total funcional.",
        )),
        minimum_per_session=policy.minimum_functional_items_per_session,
        totals=tuple(metric["total"] for metric in metrics),
    )

    score_reasons: list[str] = []
    for index, metric in enumerate(metrics):
        score_reasons.extend(
            f"{selected_ids[index]}: {reason}" for reason in metric["errors"]
        )
        if metric["score"] is not None and metric["score"] < policy.target_score:
            score_reasons.append(
                f"{selected_ids[index]} obtuvo {metric['score']:.2f}, por debajo "
                f"del objetivo interno {policy.target_score:.2f}."
            )
    scores = tuple(metric["score"] for metric in metrics)
    score_gate = _gate(
        "functional_precision_target",
        not score_reasons
        and len(scores) == policy.required_sessions
        and all(score is not None and score >= policy.target_score for score in scores),
        score_reasons or (() if len(scores) == policy.required_sessions else (
            "No hay suficientes sesiones para repetir el objetivo interno.",
        )),
        label=PRECISION_TARGET_LABEL,
        target_score=policy.target_score,
        scores=scores,
        origins=tuple(metric["score_origin"] for metric in metrics),
    )

    observed_functions = {
        int(_value(item, "function_number"))
        for metric in metrics
        for item in metric["items"]
        if str(_value(item, "function_number", "")).isdigit()
    }
    required_functions = {int(number) for number in policy.required_function_numbers}
    missing_functions = sorted(required_functions - observed_functions)
    coverage_gate = _gate(
        "joint_function_coverage",
        not missing_functions and bool(metrics),
        () if not missing_functions and metrics else (
            "La ventana de medición no cubre conjuntamente todas las funciones requeridas.",
        ),
        required=tuple(sorted(required_functions)),
        observed=tuple(sorted(observed_functions)),
        missing=tuple(missing_functions),
    )

    uniqueness_reasons: list[str] = []
    revision_sets: list[set[str]] = []
    case_sets: list[set[str]] = []
    for index, metric in enumerate(metrics):
        revisions = [_identity(_value(item, "revision_id")) for item in metric["items"]]
        cases = [_identity(_value(item, "case_id")) for item in metric["items"]]
        if "" in revisions or "" in cases:
            uniqueness_reasons.append(
                f"{selected_ids[index]} tiene ítems funcionales sin revision_id o case_id."
            )
        if len([value for value in revisions if value]) != len(
            {value for value in revisions if value}
        ):
            uniqueness_reasons.append(
                f"{selected_ids[index]} repite una revisión dentro de la sesión."
            )
        revision_sets.append({value for value in revisions if value})
        # Repeating a case inside one session is valid PJS: one case may have
        # several prompts.  Only intersections between sessions are forbidden.
        case_sets.append({value for value in cases if value})

    repeated_revisions: set[str] = set()
    repeated_cases: set[str] = set()
    for left in range(len(revision_sets)):
        for right in range(left + 1, len(revision_sets)):
            repeated_revisions.update(revision_sets[left] & revision_sets[right])
            repeated_cases.update(case_sets[left] & case_sets[right])
    if repeated_revisions:
        uniqueness_reasons.append("Hay revisiones repetidas entre sesiones de medición.")
    if repeated_cases:
        uniqueness_reasons.append("Hay casos repetidos entre sesiones de medición.")
    uniqueness_gate = _gate(
        "no_repeated_measurement_material",
        not uniqueness_reasons and len(metrics) == policy.required_sessions,
        uniqueness_reasons or (() if len(metrics) == policy.required_sessions else (
            "No hay suficientes sesiones para comprobar repeticiones.",
        )),
        repeated_revision_ids=tuple(sorted(repeated_revisions)),
        repeated_case_ids=tuple(sorted(repeated_cases)),
    )

    bank_reasons: list[str] = []
    if bank_evidence is None:
        bank_reasons.append("Falta la evidencia estructurada del banco y sus fuentes.")
    else:
        if _value(bank_evidence, "sources_verified") is not True:
            bank_reasons.append("Las fuentes del banco no están verificadas como vigentes.")
        if _value(bank_evidence, "measurement_bank_trusted") is not True:
            bank_reasons.append("El banco de medición no está marcado como confiable.")
        trusted_ids_raw = _value(bank_evidence, "trusted_revision_ids")
        if trusted_ids_raw is not None:
            trusted_ids = {_identity(value) for value in trusted_ids_raw}
            selected_revision_ids = {
                _identity(_value(item, "revision_id"))
                for metric in metrics
                for item in metric["items"]
            }
            if "" in selected_revision_ids or not selected_revision_ids.issubset(trusted_ids):
                bank_reasons.append(
                    "Una o más revisiones medidas no pertenecen al conjunto confiable."
                )
    bank_gate = _gate(
        "trusted_sources_and_bank",
        not bank_reasons and bool(selected),
        bank_reasons or (() if selected else (
            "No hay sesiones para vincular con el banco confiable.",
        )),
        note=_identity(_value(bank_evidence, "note")) if bank_evidence else "",
    )

    gates = (
        bank_gate,
        count_gate,
        partition_gate,
        completion_gate,
        assistance_gate,
        context_gate,
        recency_gate,
        totals_gate,
        score_gate,
        coverage_gate,
        uniqueness_gate,
    )
    precision_goal_met = all(gate.met for gate in gates)
    target_met_count = sum(
        score is not None and score >= policy.target_score for score in scores
    )
    repeated_label = (
        f"meta interna repetida {min(target_met_count, policy.required_sessions)}"
        f"/{policy.required_sessions}"
    )

    retention_gate = _evaluate_retention(
        retention,
        policy=policy,
        expected_context=expected_context,
        bank_evidence=bank_evidence,
        as_of=evaluated_at,
    )
    retention_goal_met: bool | None = (
        None if retention_gate.status == "pending" else retention_gate.met
    )
    if not precision_goal_met:
        status = "insufficient_internal_measurement_evidence"
    elif retention_goal_met is True:
        status = "internal_precision_and_retention_evidence_met"
    elif retention_goal_met is False:
        status = "internal_precision_met_retention_not_met"
    else:
        status = "internal_precision_met_retention_pending"

    reasons = tuple(
        reason
        for gate in gates
        if not gate.met
        for reason in gate.reasons
    )
    if retention_gate.status == "not_met":
        reasons += retention_gate.reasons

    return ReadinessAssessment(
        status=status,
        claim_status=INTERNAL_CLAIM_STATUS,
        precision_target_label=PRECISION_TARGET_LABEL,
        repeated_target_label=repeated_label,
        target_score=float(policy.target_score),
        official_functional_minimum_label=OFFICIAL_MINIMUM_LABEL,
        official_functional_minimum_score=OFFICIAL_FUNCTIONAL_MINIMUM_SCORE,
        official_result=None,
        internal_precision_goal_met=precision_goal_met,
        internal_retention_goal_met=retention_goal_met,
        selected_session_ids=selected_ids,
        session_scores=scores,
        gates=gates,
        retention_gate=retention_gate,
        reasons=reasons,
    )


__all__ = [
    "BankEvidence",
    "GateResult",
    "INTERNAL_CLAIM_STATUS",
    "ItemResult",
    "MeasurementSessionResult",
    "OFFICIAL_FUNCTIONAL_MINIMUM_SCORE",
    "OFFICIAL_MINIMUM_LABEL",
    "PRECISION_TARGET_LABEL",
    "ReadinessAssessment",
    "ReadinessPolicy",
    "RetentionEvidence",
    "evaluate_readiness",
]
