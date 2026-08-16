"""Transactional persistence for immutable OPEC simulation-policy versions."""

from __future__ import annotations

from sqlalchemy import inspect

from core.simulation_policy import (
    ResolvedSimulationPolicy,
    SimulationPolicyValidationError,
    next_policy_version,
    provisional_policy_values,
    resolve_active_policy,
)
from db.models import OpecProfile, OpecSimulationPolicy


REQUIRED_TABLES = frozenset({"opec_profiles", "opec_simulation_policies"})


class SimulationPolicyStoreError(RuntimeError):
    """The requested policy cannot be persisted without losing scope/history."""


def simulation_policy_schema_available(db) -> bool:
    return REQUIRED_TABLES.issubset(set(inspect(db.connection()).get_table_names()))


def _profile_for_scope(db, *, competition_id: int, opec_number: object) -> OpecProfile:
    profile = (
        db.query(OpecProfile)
        .filter_by(
            competition_id=int(competition_id),
            opec_number=str(opec_number or "").strip(),
        )
        .first()
    )
    if profile is None:
        raise SimulationPolicyStoreError(
            "No existe un perfil OPEC canónico para este concurso."
        )
    return profile


def _function_count(profile: OpecProfile) -> int | None:
    functions = profile.functions
    if isinstance(functions, list):
        return len(functions) or None
    if isinstance(functions, dict):
        nested = functions.get("functions")
        if isinstance(nested, (list, dict)):
            return len(nested) or None
        return len(functions) or None
    return None


def load_active_simulation_policy(
    db,
    *,
    competition_id: int,
    opec_number: object,
) -> tuple[OpecProfile, OpecSimulationPolicy | None, ResolvedSimulationPolicy]:
    """Load the only active version; absence resolves to an explicit fallback."""

    if not simulation_policy_schema_available(db):
        raise SimulationPolicyStoreError(
            "Falta aplicar la migración de políticas de simulacro (Fase 3)."
        )
    profile = _profile_for_scope(
        db,
        competition_id=competition_id,
        opec_number=opec_number,
    )
    records = (
        db.query(OpecSimulationPolicy)
        .filter_by(opec_profile_id=profile.id)
        .order_by(OpecSimulationPolicy.version_number.desc())
        .all()
    )
    active = [row for row in records if row.is_active]
    resolved = resolve_active_policy(
        records,
        opec_number=profile.opec_number,
        function_count=_function_count(profile),
    )
    return profile, (active[0] if active else None), resolved


def create_initial_simulation_policy(
    db,
    *,
    competition_id: int,
    opec_number: object,
    actor: str,
    official_partial: dict | None = None,
) -> OpecSimulationPolicy:
    """Create v1 only when the OPEC has no policy history."""

    profile, active, _ = load_active_simulation_policy(
        db,
        competition_id=competition_id,
        opec_number=opec_number,
    )
    existing = (
        db.query(OpecSimulationPolicy.id)
        .filter_by(opec_profile_id=profile.id)
        .first()
    )
    if active is not None or existing is not None:
        raise SimulationPolicyStoreError("La OPEC ya tiene historial de políticas.")
    values = provisional_policy_values(
        profile.opec_number,
        function_count=_function_count(profile),
    )
    if official_partial:
        values.update(dict(official_partial))
    values.update({
        "competition_id": profile.competition_id,
        "opec_profile_id": profile.id,
        "actor": str(actor or "").strip() or "unknown_admin",
    })
    from core.simulation_policy import validate_policy_values

    normalized = validate_policy_values(
        values,
        expected_opec_number=profile.opec_number,
    )
    row = OpecSimulationPolicy(**normalized)
    db.add(row)
    db.flush()
    return row


def create_simulation_policy_version(
    db,
    *,
    current: OpecSimulationPolicy,
    updates: dict,
    actor: str,
    change_reason: str,
) -> OpecSimulationPolicy:
    """Supersede an active row with a validated immutable next version."""

    if current is None or not current.is_active or current.active_slot != 1:
        raise SimulationPolicyStoreError("La versión de origen no está activa.")
    reason = str(change_reason or "").strip()
    if not reason:
        raise SimulationPolicyStoreError("Explica el motivo del cambio de política.")
    actor_name = str(actor or "").strip()
    if not actor_name:
        raise SimulationPolicyStoreError("La auditoría requiere identificar al actor.")

    payload = dict(updates or {})
    payload.update({
        "actor": actor_name,
        "change_reason": reason,
        "is_active": True,
    })
    try:
        normalized = next_policy_version(current, payload)
    except SimulationPolicyValidationError:
        raise

    current.is_active = False
    current.active_slot = None
    db.flush()
    row = OpecSimulationPolicy(**normalized)
    db.add(row)
    db.flush()
    return row


__all__ = [
    "SimulationPolicyStoreError",
    "create_initial_simulation_policy",
    "create_simulation_policy_version",
    "load_active_simulation_policy",
    "simulation_policy_schema_available",
]
