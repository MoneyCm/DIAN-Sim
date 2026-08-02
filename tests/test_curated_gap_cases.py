from core.curated_gap_cases import CURATED_GAP_CASES
from core.curated_gap_cases_phase2 import CURATED_GAP_CASES_PHASE2
from core.curated_gap_cases_phase3 import CURATED_GAP_CASES_PHASE3
from core.curated_gap_cases_phase4 import CURATED_GAP_CASES_PHASE4
from core.curated_gap_cases_phase5 import CURATED_GAP_CASES_PHASE5
from scripts.data.seed_curated_gap_cases import balanced_question


ALL_CURATED_CASES = (
    CURATED_GAP_CASES
    + CURATED_GAP_CASES_PHASE2
    + CURATED_GAP_CASES_PHASE3
    + CURATED_GAP_CASES_PHASE4
    + CURATED_GAP_CASES_PHASE5
)


def test_curated_gap_cases_have_official_goa_shape():
    assert len(CURATED_GAP_CASES) == 3
    for case in CURATED_GAP_CASES:
        assert len(case["questions"]) == 3
        assert case["text"]
        for question in case["questions"]:
            assert set(question["options"]) == {"A", "B", "C"}
            assert question["correct_key"] in question["options"]
            assert question["rationale"]
            assert "Compilación Jurídica DIAN" in question["source_ref"]


def test_curated_questions_are_unique():
    stems = [
        question["stem"]
        for case in CURATED_GAP_CASES
        for question in case["questions"]
    ]
    assert len(stems) == len(set(stems))


def test_complete_gap_matrix_has_fourteen_valid_cases():
    assert len(ALL_CURATED_CASES) == 14
    assert len({case["id"] for case in ALL_CURATED_CASES}) == 14
    for case in ALL_CURATED_CASES:
        assert case["text"] and len(case["questions"]) == 3
        for question in case["questions"]:
            assert set(question["options"]) == {"A", "B", "C"}
            assert question["correct_key"] in question["options"]
            assert question["rationale"] and question["source_ref"]


def test_balanced_loader_assigns_one_key_of_each_letter_per_case():
    for case in ALL_CURATED_CASES:
        keys = [balanced_question(question, index)[1] for index, question in enumerate(case["questions"])]
        assert keys == ["A", "B", "C"]
