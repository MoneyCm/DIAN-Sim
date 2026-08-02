from core.curated_gap_cases_phase7 import CURATED_GAP_CASES_PHASE7
from core.exam_format import is_official_functional_payload


def test_phase7_contains_three_current_law_goa_cases():
    assert len(CURATED_GAP_CASES_PHASE7) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE7) == 9
    for case in CURATED_GAP_CASES_PHASE7:
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
        assert all("Ley 2586 de 2026" in item["source_ref"] for item in case["questions"])
        assert all(item["rationale"] for item in case["questions"])


def test_phase7_case_and_question_ids_are_unique():
    case_ids = [case["id"] for case in CURATED_GAP_CASES_PHASE7]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE7 for item in case["questions"]]
    assert len(case_ids) == len(set(case_ids))
    assert len(stems) == len(set(stems))
