"""Administrator-only service for assigning a prepared OPEC to a user."""

from __future__ import annotations

from core.opec_lookup import find_reusable_opec, normalize_opec_number, attach_reusable_opec_to_user
from core.access_control import assert_admin_actor
from db.models import User


class AssignableOPECNotFound(ValueError):
    """Raised when an OPEC has not been prepared in the shared catalogue."""


def assign_prepared_opec(
    db,
    user_id: int,
    opec_number: object,
    *,
    actor_user_id: int | None = None,
):
    """Attach and activate a reusable public OPEC for an existing account."""
    assert_admin_actor(db, actor_user_id)
    if db.get(User, user_id) is None:
        raise ValueError("La cuenta seleccionada ya no existe.")
    number = normalize_opec_number(opec_number)
    profile = find_reusable_opec(db, number)
    if profile is None:
        raise AssignableOPECNotFound(
            "Esta OPEC aún no está preparada. Registra o verifica primero su ficha."
        )
    return attach_reusable_opec_to_user(db, user_id, profile)
