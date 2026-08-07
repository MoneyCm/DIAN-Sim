from core.guide_registry import guide_status


def test_adres_guide_registry_is_explicitly_pending_and_versioned():
    status = guide_status("ADRES-ABIERTO")
    assert status["status"] == "pending_official_guide"
    assert status["version"] == "opec-2026-08-v1"
    assert status["official_sources"] == []
