from core.curated_gap_cases_phase12 import CURATED_GAP_CASES_PHASE12
from core.exam_format import is_official_functional_payload


def test_phase12_contains_three_complete_cpaca_cases():
    assert len(CURATED_GAP_CASES_PHASE12) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE12) == 9
    for case in CURATED_GAP_CASES_PHASE12:
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
        assert all("Ley 1437 de 2011" in item["source_ref"] for item in case["questions"])
        assert all(item["rationale"] for item in case["questions"])


def test_phase12_ids_and_stems_are_unique():
    ids = [case["id"] for case in CURATED_GAP_CASES_PHASE12]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE12 for item in case["questions"]]
    assert len(ids) == len(set(ids))
    assert len(stems) == len(set(stems))
