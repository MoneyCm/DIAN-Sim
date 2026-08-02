from core.curated_gap_cases_phase8 import CURATED_GAP_CASES_PHASE8
from core.exam_format import is_official_functional_payload


def test_phase8_contains_three_complete_exchange_control_cases():
    assert len(CURATED_GAP_CASES_PHASE8) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE8) == 9
    for case in CURATED_GAP_CASES_PHASE8:
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
        assert all("Decreto Ley 2245 de 2011" in item["source_ref"] for item in case["questions"])
        assert all(item["rationale"] for item in case["questions"])


def test_phase8_ids_and_stems_are_unique():
    ids = [case["id"] for case in CURATED_GAP_CASES_PHASE8]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE8 for item in case["questions"]]
    assert len(ids) == len(set(ids))
    assert len(stems) == len(set(stems))
