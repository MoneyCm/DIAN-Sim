from core.curated_gap_cases_phase6 import CURATED_GAP_CASES_PHASE6
from core.exam_format import is_official_functional_payload


def test_phase6_contains_three_complete_source_grounded_cases():
    assert len(CURATED_GAP_CASES_PHASE6) == 3
    for case in CURATED_GAP_CASES_PHASE6:
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
        assert all(item["source_ref"].startswith("UAE DIAN") for item in case["questions"])
