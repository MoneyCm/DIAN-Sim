from core.curated_gap_cases_phase14 import CURATED_GAP_CASES_PHASE14
from core.exam_format import is_official_functional_payload


def test_phase14_contains_three_complete_f4_f9_cases():
    assert len(CURATED_GAP_CASES_PHASE14) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE14) == 9
    for case in CURATED_GAP_CASES_PHASE14:
        payload = {
            "text": case["text"],
            "questions": [
                {
                    "track": "FUNCIONAL",
                    "stem": item["stem"],
                    "options": item["options"],
                    "correct_key": item["correct_key"],
                }
                for item in case["questions"]
            ],
        }
        assert is_official_functional_payload(payload)
        assert all(item["correct_key"] == "A" for item in case["questions"])
        assert all("DIAN" in item["source_ref"] for item in case["questions"])
        assert all(item["rationale"] for item in case["questions"])


def test_phase14_ids_and_stems_are_unique():
    ids = [case["id"] for case in CURATED_GAP_CASES_PHASE14]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE14 for item in case["questions"]]
    assert len(ids) == len(set(ids))
    assert len(stems) == len(set(stems))


def test_phase14_covers_both_functions_and_current_procedures():
    topics = " ".join(case["topic"] for case in CURATED_GAP_CASES_PHASE14)
    sources = " ".join(
        item["source_ref"]
        for case in CURATED_GAP_CASES_PHASE14
        for item in case["questions"]
    )
    assert "F4" in topics
    assert "F9" in topics
    assert "PR-COA-0501" in sources
    assert "PR-COT-0432" in sources
    assert "versión 3" in sources
