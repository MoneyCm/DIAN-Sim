from types import SimpleNamespace

from core.real_exam import (
    EXAM_PARAMETERS_STATUS,
    PJS_METHODOLOGY_STATUS,
    UAPA_COMPETITION_CODE,
    blueprint_for_competition,
    select_balanced_blocks,
)


def test_uapa_blueprint_has_thirty_questions_and_sixty_minutes():
    blueprint = blueprint_for_competition(UAPA_COMPETITION_CODE)
    assert blueprint.target_cases == 10
    assert blueprint.target_questions == 30
    assert blueprint.target_minutes == 60


def test_default_blueprint_preserves_free_and_pro_limits():
    assert blueprint_for_competition("DIAN-2676", is_pro=False).target_cases == 2
    assert blueprint_for_competition("DIAN-2676", is_pro=True).target_cases == 3


def test_generic_competition_scales_from_reviewed_inventory():
    assert blueprint_for_competition("NUEVO", reviewed_case_count=10).target_questions == 30
    assert blueprint_for_competition("NUEVO", reviewed_case_count=20).target_questions == 60
    assert blueprint_for_competition("NUEVO", reviewed_case_count=6).target_questions == 18


def test_sixty_question_and_120_minute_plan_is_explicitly_provisional():
    blueprint = blueprint_for_competition("DIAN-2676", reviewed_case_count=20)

    assert blueprint.target_questions == 60
    assert blueprint.target_minutes == 120
    assert "configuración provisional" in blueprint.title.lower()
    assert blueprint.parameter_status == EXAM_PARAMETERS_STATUS
    assert blueprint.methodology_status == PJS_METHODOLOGY_STATUS
    assert blueprint.official_question_count is None
    assert blueprint.official_duration_minutes is None


def test_legacy_case_count_argument_is_inventory_alias_not_official_quantity():
    blueprint = blueprint_for_competition("DIAN-2676", official_case_count=20)
    assert blueprint.target_questions == 60
    assert blueprint.official_question_count is None


def test_provisional_timing_is_editable_without_changing_pjs_basis():
    blueprint = blueprint_for_competition(
        "DIAN-2676",
        reviewed_case_count=20,
        questions_per_case=2,
        minutes_per_question=3,
    )
    assert blueprint.target_questions == 40
    assert blueprint.target_minutes == 120
    assert blueprint.methodology_status == PJS_METHODOLOGY_STATUS


def test_versioned_policy_can_request_exact_question_total_and_decimal_timing():
    blueprint = blueprint_for_competition(
        "DIAN-2676",
        target_question_count=45,
        questions_per_case=3,
        minutes_per_question=1.5,
        navigation_mode="free",
    )

    assert blueprint.target_cases == 15
    assert blueprint.target_questions == 45
    assert blueprint.target_minutes == 68
    assert blueprint.navigation_mode == "free"
    assert "interna provisional" in blueprint.title.lower()


def test_balanced_selection_spreads_topics_before_repeating():
    blocks = [
        SimpleNamespace(id="a1", topic="A"), SimpleNamespace(id="a2", topic="A"),
        SimpleNamespace(id="b1", topic="B"), SimpleNamespace(id="c1", topic="C"),
    ]
    selected = select_balanced_blocks(blocks, 3)
    assert {block.topic for block in selected} == {"A", "B", "C"}


def test_preferred_topic_is_selected_first():
    blocks = [SimpleNamespace(id="a", topic="A"), SimpleNamespace(id="b", topic="B")]
    assert select_balanced_blocks(blocks, 1, ["B"])[0].topic == "B"
