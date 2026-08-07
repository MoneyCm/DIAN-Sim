from datetime import datetime, timedelta
from types import SimpleNamespace

from core.opec_profiles import unique_opec_profiles


def profile(profile_id, opec, *, active=False, minutes_old=0):
    return SimpleNamespace(
        id=profile_id,
        opec_number=opec,
        is_active=active,
        updated_at=datetime(2026, 1, 1) - timedelta(minutes=minutes_old),
    )


def test_unique_opec_profiles_collapses_duplicates_and_prefers_active():
    old = profile(1, "242934", minutes_old=20)
    active = profile(2, "242934", active=True, minutes_old=30)
    adres = profile(3, "252097")

    result = unique_opec_profiles([old, active, adres])

    assert {item.opec_number for item in result} == {"242934", "252097"}
    assert next(item for item in result if item.opec_number == "242934").id == 2


def test_unique_opec_profiles_prefers_latest_when_none_is_active():
    latest = profile(2, "241130", minutes_old=1)
    older = profile(1, "241130", minutes_old=10)

    assert unique_opec_profiles([older, latest]) == [latest]
