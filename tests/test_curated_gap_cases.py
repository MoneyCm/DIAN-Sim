from core.curated_gap_cases import CURATED_GAP_CASES


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
