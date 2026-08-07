"""Helpers for presenting a user's OPEC profiles without duplicates."""


def unique_opec_profiles(profiles):
    """Keep one profile per OPEC, preferring active and then most recent rows."""
    ordered = sorted(
        profiles,
        key=lambda profile: (
            bool(getattr(profile, "is_active", False)),
            getattr(profile, "updated_at", None) is not None,
            getattr(profile, "updated_at", None),
            getattr(profile, "id", 0),
        ),
        reverse=True,
    )
    unique = {}
    for profile in ordered:
        key = str(getattr(profile, "opec_number", "") or "").strip()
        if key and key not in unique:
            unique[key] = profile
    return list(unique.values())
