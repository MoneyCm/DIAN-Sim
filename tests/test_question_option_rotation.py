import pytest

from core.question_option_rotation import OptionRotationError, rotate_correct_option


def test_rotation_swaps_positions_and_preserves_every_option():
    original = {"A": "Correcta", "B": "Distractor uno", "C": "Distractor dos"}

    rotated = rotate_correct_option(original, old_key="A", new_key="C")

    assert rotated == {
        "A": "Distractor dos",
        "B": "Distractor uno",
        "C": "Correcta",
    }
    assert set(rotated.values()) == set(original.values())


def test_rotation_rejects_duplicate_options_instead_of_compounding_damage():
    with pytest.raises(OptionRotationError, match="duplicadas"):
        rotate_correct_option(
            {"A": "Repetida", "B": "Repetida", "C": "Correcta"},
            old_key="C",
            new_key="A",
        )
