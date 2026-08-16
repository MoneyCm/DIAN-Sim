from dataclasses import dataclass

from core.exposure_control import (
    block_is_novel,
    exposure_snapshot,
    select_novel_measurement_blocks,
)


@dataclass
class Event:
    question_id: str
    case_id: str
    question_revision_id: str


@dataclass
class Question:
    question_id: str
    case_id: str


@dataclass
class Block:
    id: str
    topic: str
    questions: list


def _block(case_id, topic, number):
    return Block(
        id=f"{case_id}-pjs-1",
        topic=topic,
        questions=[Question(f"q{number}-{index}", case_id) for index in range(3)],
    )


def test_snapshot_counts_each_exposure_dimension():
    snapshot = exposure_snapshot(
        [Event("q1", "c1", "r1"), Event("q1", "c1", "r2")]
    )
    assert snapshot.question_count("q1") == 2
    assert snapshot.case_count("c1") == 2
    assert snapshot.revision_count("r1") == 1


def test_any_prior_case_exposure_blocks_all_variants_from_that_case():
    snapshot = exposure_snapshot([Event("old", "c1", "r1")])
    assert block_is_novel(_block("c1", "A", 1), snapshot) is False


def test_any_prior_question_exposure_blocks_a_block_even_without_case_id_match():
    block = _block("c2", "A", 2)
    snapshot = exposure_snapshot([Event("q2-1", "legacy-case", "r1")])
    assert block_is_novel(block, snapshot) is False


def test_strict_selection_never_reuses_seen_material_to_fill_target():
    blocks = [_block("c1", "A", 1), _block("c2", "B", 2), _block("c3", "C", 3)]
    snapshot = exposure_snapshot([Event("q1-0", "c1", "r1")])
    result = select_novel_measurement_blocks(
        blocks,
        target_count=3,
        snapshot=snapshot,
    )
    assert len(result.blocks) == 2
    assert result.complete is False
    assert "ampliarse" in result.reason
    assert all(block.id != "c1-pjs-1" for block in result.blocks)


def test_strict_selection_is_deterministic_balanced_and_complete_when_possible():
    blocks = [
        _block("c3", "Tributario", 3),
        _block("c1", "Aduanero", 1),
        _block("c2", "Tributario", 2),
    ]
    result = select_novel_measurement_blocks(
        blocks,
        target_count=2,
        snapshot=exposure_snapshot([]),
        preferred_topics=("Tributario",),
    )
    assert result.complete is True
    assert [block.topic for block in result.blocks] == ["Tributario", "Aduanero"]


def test_zero_target_is_not_a_valid_complete_measurement():
    result = select_novel_measurement_blocks(
        [_block("c1", "A", 1)],
        target_count=0,
        snapshot=exposure_snapshot([]),
    )
    assert result.blocks == ()
    assert result.complete is False
