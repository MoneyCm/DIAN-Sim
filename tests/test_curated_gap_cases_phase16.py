from core.curated_gap_cases_phase16 import CURATED_GAP_CASES_PHASE16
from core.exam_format import is_official_functional_payload


def test_phase16_contains_three_complete_common_function_cases():
    assert len(CURATED_GAP_CASES_PHASE16) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE16) == 9
    for case in CURATED_GAP_CASES_PHASE16:
        assert case["topic"].startswith("F9 - ")
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
        assert all("Resolución DIAN 000067 de 2024" in item["source_ref"] for item in case["questions"])
        assert all("AT-FL-3006" in item["source_ref"] for item in case["questions"])
        assert all(item["rationale"] for item in case["questions"])


def test_phase16_ids_and_stems_are_unique():
    ids = [case["id"] for case in CURATED_GAP_CASES_PHASE16]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE16 for item in case["questions"]]
    assert len(ids) == len(set(ids))
    assert len(stems) == len(set(stems))


def test_phase16_covers_the_express_common_function_numerals():
    sources = " ".join(
        item["source_ref"]
        for case in CURATED_GAP_CASES_PHASE16
        for item in case["questions"]
    )
    for numeral in ("1", "2", "3", "4", "6", "7", "8", "11", "12"):
        assert f"{numeral}" in sources
