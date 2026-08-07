from types import SimpleNamespace

from core.real_exam import (
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
