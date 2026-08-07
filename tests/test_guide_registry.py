from core.guide_registry import guide_status


def test_adres_guide_registry_is_explicitly_pending_and_versioned():
    status = guide_status("ADRES-ABIERTO")
    assert status["status"] == "pending_official_guide"
    assert status["version"] == "opec-2026-08-v1"
    assert status["official_sources"] == []


def test_every_new_competition_starts_with_a_versioned_provisional_matrix():
    status = guide_status("CONCURSO-NUEVO")
    assert status["status"] == "pending_official_guide"
    assert status["version"] == "opec-base-v1"
