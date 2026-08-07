from core.competition_readiness import CompetitionReadiness


def test_readiness_contract_exposes_generic_onboarding_fields():
    readiness = CompetitionReadiness(100, 70, 30, 10, 30, 60, "Listo")
    assert readiness.exam_questions == 30
    assert readiness.exam_minutes == 60
    assert readiness.official_case_count == 10
