from core.guide_registry import guide_status


def test_adres_guide_registry_records_the_official_selection_framework():
    status = guide_status("ADRES-ABIERTO")
    assert status["status"] == "official_framework_loaded"
    assert status["version"] == "cnsc-2026-04-30"
    assert len(status["official_sources"]) == 3


def test_every_new_competition_starts_with_a_versioned_provisional_matrix():
    status = guide_status("CONCURSO-NUEVO")
    assert status["status"] == "pending_official_guide"
    assert status["version"] == "opec-base-v1"
