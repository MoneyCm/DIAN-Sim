"""Safe user-scoped operations for selecting a study OPEC."""

from __future__ import annotations

from db.models import UserOPEC


class OPECNotFoundForUser(ValueError):
    """Raised when a user tries to activate a position that is not theirs."""


def activate_opec(db, user_id: int, opec_id: int) -> UserOPEC:
    """Make exactly one of the user's OPEC records the active study target."""
    target = db.query(UserOPEC).filter_by(id=opec_id, user_id=user_id).first()
    if target is None:
        raise OPECNotFoundForUser("La OPEC no pertenece a esta cuenta.")
    db.query(UserOPEC).filter_by(user_id=user_id).update(
        {UserOPEC.is_active: False}, synchronize_session=False
    )
    target.is_active = True
    return target
