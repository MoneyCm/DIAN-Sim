from datetime import date

from core.study_recommendations import FunctionEvidence, build_daily_mission


def test_daily_mission_targets_the_weakest_undercovered_function():
    evidence = [
        FunctionEvidence(1, mastery_score=90, attempts=20, trusted_question_count=90),
        FunctionEvidence(
            2,
            mastery_score=20,
            attempts=2,
            trusted_question_count=3,
            due_error_count=4,
            question_ids=("q1", "q2", "q3"),
        ),
    ]
    mission = build_daily_mission(
        opec_number="236769",
        available_minutes=30,
        function_evidence=evidence,
        exam_date=date(2026, 12, 15),
        today=date(2026, 8, 15),
    )
    assert mission is not None
    assert mission.function_number == 2
    assert mission.total_minutes == 30
    assert sum(item.minutes for item in mission.activities) == 30
    assert mission.question_ids == ("q1", "q2", "q3")


def test_target_85_is_explicitly_internal_and_source_is_official():
    mission = build_daily_mission(opec_number=236769, available_minutes=60)
    assert mission.target_score == 85
    assert "interno" in mission.target_status
    assert mission.source is not None
    assert mission.source.url.startswith("https://")
    assert mission.source.locator_verified is True


def test_daily_mission_uses_editable_internal_target_without_claiming_official_cut():
    mission = build_daily_mission(
        opec_number=236769,
        available_minutes=30,
        target_score=91.5,
    )
    assert mission.target_score == 91.5
    assert "interno" in mission.target_status


def test_unknown_opec_does_not_get_an_invented_plan():
    assert build_daily_mission(opec_number="999999", available_minutes=30) is None


def test_vague_source_locator_is_never_presented_as_precise(monkeypatch):
    from core import study_recommendations as module

    monkeypatch.setattr(
        module,
        "load_preparation_blueprint",
        lambda _: {
            "target_score": 85,
            "sources": [
                {
                    "id": "law",
                    "name": "Norma",
                    "url": "https://example.test/law",
                    "locators": "Artículo aplicable indicado en cada pregunta",
                    "validity": "Vigente",
                    "status": "official_available",
                }
            ],
            "functions": [
                {
                    "number": 1,
                    "short_name": "Tema",
                    "knowledge": ["Regla"],
                    "source_ids": ["law"],
                    "functional_question_target": 10,
                }
            ],
        },
    )
    mission = module.build_daily_mission(opec_number="1", available_minutes=30)
    assert mission.source.locator_verified is False
    assert "biblioteca confirme" in mission.activities[1].instruction
