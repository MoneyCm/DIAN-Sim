"""Pure, versioned policy rules for OPEC-specific practice simulations.

This module does not query the database and does not select questions.  It
keeps editable product parameters separate from nullable facts supported by an
official publication so callers cannot accidentally label defaults as official.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any
from urllib.parse import urlparse


POLICY_STATUSES = frozenset({"draft", "provisional", "verified", "retired"})
OFFICIAL_SOURCE_STATUSES = frozenset({
    "unpublished",
    "pending_verification",
    "partial",
    "verified_current",
    "superseded",
})
NAVIGATION_MODES = frozenset({"sequential", "free", "case_locked"})
SIMULATION_MODES = ("diagnostic", "short", "partial", "full")
MODE_LABELS = {
    "diagnostic": "Diagnóstico",
    "short": "Corto",
    "partial": "Parcial",
    "full": "Completo",
}

_INTERNAL_FIELDS = (
    "internal_diagnostic_questions",
    "internal_short_questions",
    "internal_partial_questions",
    "internal_full_questions",
    "internal_minutes_per_question",
    "internal_max_questions_per_case",
    "internal_navigation_mode",
    "internal_composition_json",
    "internal_weights_json",
)
_OFFICIAL_FIELDS = (
    "official_question_count",
    "official_duration_minutes",
    "official_minutes_per_question",
    "official_max_questions_per_case",
    "official_navigation_mode",
    "official_composition_json",
    "official_weights_json",
    "official_source_title",
    "official_source_url",
    "official_source_version",
    "official_source_status",
    "official_published_at",
    "official_verified_at",
)
_EDITABLE_FIELDS = frozenset({
    *_INTERNAL_FIELDS,
    *_OFFICIAL_FIELDS,
    "policy_status",
    "is_active",
    "change_reason",
    "actor",
})


class SimulationPolicyValidationError(ValueError):
    """The policy could produce ambiguous or unsupported exam claims."""


@dataclass(frozen=True)
class SimulationMode:
    key: str
    label: str
    question_count: int
    duration_minutes: int


@dataclass(frozen=True)
class InternalSimulationParameters:
    modes: tuple[SimulationMode, ...]
    minutes_per_question: float
    max_questions_per_case: int
    navigation_mode: str
    composition: dict[str, float]
    weights: dict[str, float]

    def mode(self, key: str) -> SimulationMode:
        for item in self.modes:
            if item.key == key:
                return item
        raise KeyError(key)


@dataclass(frozen=True)
class OfficialSimulationParameters:
    question_count: int | None
    duration_minutes: int | None
    minutes_per_question: float | None
    max_questions_per_case: int | None
    navigation_mode: str | None
    composition: dict[str, float] | None
    weights: dict[str, float] | None
    source_title: str | None
    source_url: str | None
    source_version: str | None
    source_status: str | None
    published_at: datetime | None
    verified_at: datetime | None

    @property
    def has_published_parameters(self) -> bool:
        return any((
            self.question_count is not None,
            self.duration_minutes is not None,
            self.minutes_per_question is not None,
            self.max_questions_per_case is not None,
            self.navigation_mode is not None,
            self.composition is not None,
            self.weights is not None,
        ))


@dataclass(frozen=True)
class ResolvedSimulationPolicy:
    opec_number: str
    version_number: int
    policy_version: str
    policy_status: str
    is_active: bool
    active_slot: int | None
    internal: InternalSimulationParameters
    official: OfficialSimulationParameters
    supersedes_policy_id: str | None = None

    @property
    def is_provisional(self) -> bool:
        return self.policy_status in {"draft", "provisional"}


def provisional_policy_values(
    opec_number: object,
    *,
    version_number: int = 1,
    function_count: int | None = None,
) -> dict[str, Any]:
    """Return explicit product defaults; every official field stays ``None``."""

    number = str(opec_number or "").strip()
    if not number:
        raise SimulationPolicyValidationError("La política requiere un número OPEC.")
    if int(version_number) < 1:
        raise SimulationPolicyValidationError("La versión debe ser mayor o igual a 1.")
    diagnostic_count = (
        9
        if function_count is None
        else _positive_int(function_count, "function_count", maximum=5000)
    )
    short_count = max(15, diagnostic_count)
    partial_count = max(30, short_count)
    full_count = max(60, partial_count)
    values: dict[str, Any] = {
        "opec_number": number,
        "version_number": int(version_number),
        "policy_version": f"opec-{number}-simulation-v{int(version_number)}",
        "supersedes_policy_id": None,
        "policy_status": "provisional",
        "is_active": True,
        "active_slot": 1,
        "internal_diagnostic_questions": diagnostic_count,
        "internal_short_questions": short_count,
        "internal_partial_questions": partial_count,
        "internal_full_questions": full_count,
        "internal_minutes_per_question": 2.0,
        "internal_max_questions_per_case": 3,
        "internal_navigation_mode": "sequential",
        "internal_composition_json": {"functional": 1.0},
        "internal_weights_json": {"functional": 1.0},
        "change_reason": "Configuración interna provisional editable.",
        "actor": "system_default",
    }
    values.update({field: None for field in _OFFICIAL_FIELDS})
    return values


def _read(source: object, field: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(field, default)
    return getattr(source, field, default)


def _positive_int(value: object, field: str, *, maximum: int) -> int:
    if isinstance(value, bool):
        raise SimulationPolicyValidationError(f"{field} debe ser un entero positivo.")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise SimulationPolicyValidationError(
            f"{field} debe ser un entero positivo."
        ) from exc
    if result < 1 or result > maximum or result != value:
        raise SimulationPolicyValidationError(
            f"{field} debe estar entre 1 y {maximum}."
        )
    return result


def _positive_float(value: object, field: str, *, maximum: float) -> float:
    if isinstance(value, bool):
        raise SimulationPolicyValidationError(f"{field} debe ser un número positivo.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SimulationPolicyValidationError(
            f"{field} debe ser un número positivo."
        ) from exc
    if not math.isfinite(result) or result <= 0 or result > maximum:
        raise SimulationPolicyValidationError(
            f"{field} debe ser mayor que 0 y menor o igual a {maximum}."
        )
    return result


def _share_map(value: object, field: str) -> dict[str, float]:
    if not isinstance(value, Mapping) or not value:
        raise SimulationPolicyValidationError(
            f"{field} debe ser un objeto JSON no vacío."
        )
    parsed: dict[str, float] = {}
    for raw_key, raw_share in value.items():
        key = str(raw_key or "").strip()
        if not key or len(key) > 100 or isinstance(raw_share, bool):
            raise SimulationPolicyValidationError(
                f"{field} contiene una categoría o proporción inválida."
            )
        try:
            share = float(raw_share)
        except (TypeError, ValueError) as exc:
            raise SimulationPolicyValidationError(
                f"{field} solo admite proporciones numéricas."
            ) from exc
        if not math.isfinite(share) or share < 0:
            raise SimulationPolicyValidationError(
                f"{field} no admite proporciones negativas o no finitas."
            )
        parsed[key] = share
    total = sum(parsed.values())
    if total <= 0:
        raise SimulationPolicyValidationError(
            f"{field} debe contener al menos una proporción positiva."
        )
    if not (math.isclose(total, 1.0, abs_tol=1e-6) or math.isclose(
        total, 100.0, abs_tol=1e-6
    )):
        raise SimulationPolicyValidationError(
            f"{field} debe sumar 1.0 o 100.0."
        )
    return {key: round(share / total, 8) for key, share in parsed.items()}


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _valid_url(value: str | None, *, verified: bool) -> bool:
    if value is None:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ({"https"} if verified else {"http", "https"}) and bool(
        parsed.netloc
    )


def validate_policy_values(
    source: object,
    *,
    expected_opec_number: object | None = None,
) -> dict[str, Any]:
    """Validate and normalize a mapping or ORM-like policy record."""

    number = _optional_text(_read(source, "opec_number"))
    if number is None:
        raise SimulationPolicyValidationError("La política requiere un número OPEC.")
    if expected_opec_number is not None and number != str(expected_opec_number).strip():
        raise SimulationPolicyValidationError("La política pertenece a otra OPEC.")

    version_number = _positive_int(
        _read(source, "version_number"), "version_number", maximum=100000
    )
    policy_version = _optional_text(_read(source, "policy_version"))
    if policy_version is None:
        raise SimulationPolicyValidationError("policy_version es obligatorio.")
    policy_status = _optional_text(_read(source, "policy_status"))
    if policy_status not in POLICY_STATUSES:
        raise SimulationPolicyValidationError("Estado de política no válido.")
    raw_is_active = _read(source, "is_active", True)
    if not isinstance(raw_is_active, bool):
        raise SimulationPolicyValidationError("is_active debe ser booleano.")
    is_active = raw_is_active
    if is_active and policy_status == "retired":
        raise SimulationPolicyValidationError(
            "Una política retirada no puede permanecer activa."
        )
    raw_active_slot = _read(source, "active_slot", 1 if is_active else None)
    active_slot = (
        _positive_int(raw_active_slot, "active_slot", maximum=1)
        if raw_active_slot is not None
        else None
    )
    if (is_active and active_slot != 1) or (not is_active and active_slot is not None):
        raise SimulationPolicyValidationError(
            "active_slot debe ser 1 solo para la versión activa."
        )

    counts = {
        "diagnostic": _positive_int(
            _read(source, "internal_diagnostic_questions"),
            "internal_diagnostic_questions",
            maximum=5000,
        ),
        "short": _positive_int(
            _read(source, "internal_short_questions"),
            "internal_short_questions",
            maximum=5000,
        ),
        "partial": _positive_int(
            _read(source, "internal_partial_questions"),
            "internal_partial_questions",
            maximum=5000,
        ),
        "full": _positive_int(
            _read(source, "internal_full_questions"),
            "internal_full_questions",
            maximum=5000,
        ),
    }
    if list(counts.values()) != sorted(counts.values()):
        raise SimulationPolicyValidationError(
            "Los tamaños deben cumplir diagnóstico <= corto <= parcial <= completo."
        )
    minutes = _positive_float(
        _read(source, "internal_minutes_per_question"),
        "internal_minutes_per_question",
        maximum=60.0,
    )
    max_per_case = _positive_int(
        _read(source, "internal_max_questions_per_case"),
        "internal_max_questions_per_case",
        maximum=10,
    )
    navigation = _optional_text(_read(source, "internal_navigation_mode"))
    if navigation not in NAVIGATION_MODES:
        raise SimulationPolicyValidationError("Navegación interna no válida.")
    internal_composition = _share_map(
        _read(source, "internal_composition_json"),
        "internal_composition_json",
    )
    internal_weights = _share_map(
        _read(source, "internal_weights_json"),
        "internal_weights_json",
    )
    if set(internal_composition) != set(internal_weights):
        raise SimulationPolicyValidationError(
            "Composición y pesos internos deben usar las mismas categorías."
        )

    official_question_count = _read(source, "official_question_count")
    if official_question_count is not None:
        official_question_count = _positive_int(
            official_question_count, "official_question_count", maximum=5000
        )
    official_duration = _read(source, "official_duration_minutes")
    if official_duration is not None:
        official_duration = _positive_int(
            official_duration, "official_duration_minutes", maximum=1440
        )
    official_minutes = _read(source, "official_minutes_per_question")
    if official_minutes is not None:
        official_minutes = _positive_float(
            official_minutes, "official_minutes_per_question", maximum=60.0
        )
    official_max_case = _read(source, "official_max_questions_per_case")
    if official_max_case is not None:
        official_max_case = _positive_int(
            official_max_case, "official_max_questions_per_case", maximum=10
        )
    official_navigation = _optional_text(_read(source, "official_navigation_mode"))
    if official_navigation is not None and official_navigation not in NAVIGATION_MODES:
        raise SimulationPolicyValidationError("Navegación oficial no válida.")
    raw_official_composition = _read(source, "official_composition_json")
    official_composition = (
        _share_map(raw_official_composition, "official_composition_json")
        if raw_official_composition is not None
        else None
    )
    raw_official_weights = _read(source, "official_weights_json")
    official_weights = (
        _share_map(raw_official_weights, "official_weights_json")
        if raw_official_weights is not None
        else None
    )
    if (
        official_composition is not None
        and official_weights is not None
        and set(official_composition) != set(official_weights)
    ):
        raise SimulationPolicyValidationError(
            "Composición y pesos oficiales deben usar las mismas categorías."
        )

    source_title = _optional_text(_read(source, "official_source_title"))
    source_url = _optional_text(_read(source, "official_source_url"))
    source_version = _optional_text(_read(source, "official_source_version"))
    source_status = _optional_text(_read(source, "official_source_status"))
    if source_status is not None and source_status not in OFFICIAL_SOURCE_STATUSES:
        raise SimulationPolicyValidationError("Estado de fuente oficial no válido.")
    published_at = _read(source, "official_published_at")
    verified_at = _read(source, "official_verified_at")
    official_values = (
        official_question_count,
        official_duration,
        official_minutes,
        official_max_case,
        official_navigation,
        official_composition,
        official_weights,
    )
    has_official_values = any(value is not None for value in official_values)
    if source_status == "unpublished" and has_official_values:
        raise SimulationPolicyValidationError(
            "No puede haber parámetros oficiales si la fuente figura como no publicada."
        )
    if has_official_values and not (
        source_url and source_version and source_status
    ):
        raise SimulationPolicyValidationError(
            "Todo parámetro oficial requiere URL, versión y estado de fuente."
        )
    if source_url and not _valid_url(
        source_url, verified=source_status == "verified_current"
    ):
        raise SimulationPolicyValidationError("La URL oficial no es válida.")
    if policy_status == "verified" and not (
        has_official_values
        and
        source_status == "verified_current"
        and source_url
        and source_version
        and verified_at is not None
    ):
        raise SimulationPolicyValidationError(
            "Una política verificada requiere fuente HTTPS vigente y fecha de verificación."
        )

    normalized: dict[str, Any] = {
        "opec_number": number,
        "version_number": version_number,
        "policy_version": policy_version,
        "supersedes_policy_id": _optional_text(
            _read(source, "supersedes_policy_id")
        ),
        "policy_status": policy_status,
        "is_active": is_active,
        "active_slot": active_slot,
        "internal_diagnostic_questions": counts["diagnostic"],
        "internal_short_questions": counts["short"],
        "internal_partial_questions": counts["partial"],
        "internal_full_questions": counts["full"],
        "internal_minutes_per_question": minutes,
        "internal_max_questions_per_case": max_per_case,
        "internal_navigation_mode": navigation,
        "internal_composition_json": internal_composition,
        "internal_weights_json": internal_weights,
        "official_question_count": official_question_count,
        "official_duration_minutes": official_duration,
        "official_minutes_per_question": official_minutes,
        "official_max_questions_per_case": official_max_case,
        "official_navigation_mode": official_navigation,
        "official_composition_json": official_composition,
        "official_weights_json": official_weights,
        "official_source_title": source_title,
        "official_source_url": source_url,
        "official_source_version": source_version,
        "official_source_status": source_status,
        "official_published_at": published_at,
        "official_verified_at": verified_at,
        "change_reason": _optional_text(_read(source, "change_reason")),
        "actor": _optional_text(_read(source, "actor")),
    }
    for identity_field in ("competition_id", "opec_profile_id"):
        value = _read(source, identity_field)
        if value is not None:
            normalized[identity_field] = _positive_int(
                value, identity_field, maximum=2_147_483_647
            )
    return normalized


def resolve_simulation_policy(
    source: object | None,
    *,
    opec_number: object,
    function_count: int | None = None,
) -> ResolvedSimulationPolicy:
    """Resolve one record or a clearly provisional default configuration."""

    values = (
        provisional_policy_values(opec_number, function_count=function_count)
        if source is None
        else validate_policy_values(source, expected_opec_number=opec_number)
    )
    if source is None:
        values = validate_policy_values(values, expected_opec_number=opec_number)
    minutes = values["internal_minutes_per_question"]
    modes = tuple(
        SimulationMode(
            key=key,
            label=MODE_LABELS[key],
            question_count=values[f"internal_{key}_questions"],
            duration_minutes=math.ceil(
                values[f"internal_{key}_questions"] * minutes
            ),
        )
        for key in SIMULATION_MODES
    )
    return ResolvedSimulationPolicy(
        opec_number=values["opec_number"],
        version_number=values["version_number"],
        policy_version=values["policy_version"],
        policy_status=values["policy_status"],
        is_active=values["is_active"],
        active_slot=values["active_slot"],
        supersedes_policy_id=values["supersedes_policy_id"],
        internal=InternalSimulationParameters(
            modes=modes,
            minutes_per_question=minutes,
            max_questions_per_case=values["internal_max_questions_per_case"],
            navigation_mode=values["internal_navigation_mode"],
            composition=values["internal_composition_json"],
            weights=values["internal_weights_json"],
        ),
        official=OfficialSimulationParameters(
            question_count=values["official_question_count"],
            duration_minutes=values["official_duration_minutes"],
            minutes_per_question=values["official_minutes_per_question"],
            max_questions_per_case=values["official_max_questions_per_case"],
            navigation_mode=values["official_navigation_mode"],
            composition=values["official_composition_json"],
            weights=values["official_weights_json"],
            source_title=values["official_source_title"],
            source_url=values["official_source_url"],
            source_version=values["official_source_version"],
            source_status=values["official_source_status"],
            published_at=values["official_published_at"],
            verified_at=values["official_verified_at"],
        ),
    )


def validate_policy_scope(source: object, opec_profile: object) -> dict[str, Any]:
    """Validate duplicated scope snapshots against their canonical profile."""

    values = validate_policy_values(
        source,
        expected_opec_number=_read(opec_profile, "opec_number"),
    )
    expected_profile_id = _read(opec_profile, "id")
    expected_competition_id = _read(opec_profile, "competition_id")
    if (
        values.get("opec_profile_id") != expected_profile_id
        or values.get("competition_id") != expected_competition_id
    ):
        raise SimulationPolicyValidationError(
            "La política no coincide con el perfil OPEC o su concurso."
        )
    return values


def resolve_active_policy(
    records: Sequence[object],
    *,
    opec_number: object,
    function_count: int | None = None,
) -> ResolvedSimulationPolicy:
    """Resolve exactly one active version, or an explicit provisional default."""

    target = str(opec_number or "").strip()
    active = [
        row for row in records
        if bool(_read(row, "is_active", False))
        and str(_read(row, "opec_number", "")).strip() == target
    ]
    if not active:
        return resolve_simulation_policy(
            None,
            opec_number=target,
            function_count=function_count,
        )
    if len(active) != 1:
        raise SimulationPolicyValidationError(
            "La OPEC tiene más de una política de simulacro activa."
        )
    return resolve_simulation_policy(active[0], opec_number=target)


def next_policy_version(
    current: object,
    updates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build validated kwargs for a new row; never mutates the current version."""

    current_values = validate_policy_values(current)
    changes = dict(updates or {})
    forbidden = set(changes) - _EDITABLE_FIELDS
    if forbidden:
        raise SimulationPolicyValidationError(
            "Campos no editables: " + ", ".join(sorted(forbidden))
        )
    next_values = dict(current_values)
    next_values.update(changes)
    next_number = current_values["version_number"] + 1
    next_values.update({
        "version_number": next_number,
        "policy_version": (
            f"opec-{current_values['opec_number']}-simulation-v{next_number}"
        ),
        "supersedes_policy_id": _optional_text(_read(current, "id")),
        "policy_status": changes.get("policy_status", "draft"),
        "is_active": changes.get("is_active", True),
        "active_slot": 1 if changes.get("is_active", True) else None,
    })
    return validate_policy_values(
        next_values,
        expected_opec_number=current_values["opec_number"],
    )


__all__ = [
    "InternalSimulationParameters",
    "NAVIGATION_MODES",
    "OFFICIAL_SOURCE_STATUSES",
    "OfficialSimulationParameters",
    "POLICY_STATUSES",
    "ResolvedSimulationPolicy",
    "SIMULATION_MODES",
    "SimulationMode",
    "SimulationPolicyValidationError",
    "next_policy_version",
    "provisional_policy_values",
    "resolve_active_policy",
    "resolve_simulation_policy",
    "validate_policy_scope",
    "validate_policy_values",
]
