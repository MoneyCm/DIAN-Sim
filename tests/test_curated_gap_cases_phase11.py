from core.curated_gap_cases_phase11 import CURATED_GAP_CASES_PHASE11
from core.exam_format import is_official_functional_payload


def test_phase11_contains_three_complete_refund_cases():
    assert len(CURATED_GAP_CASES_PHASE11) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE11) == 9
    for case in CURATED_GAP_CASES_PHASE11:
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
        assert all("Estatuto Tributario" in item["source_ref"] for item in case["questions"])
        assert all(item["rationale"] for item in case["questions"])


def test_phase11_ids_and_stems_are_unique():
    ids = [case["id"] for case in CURATED_GAP_CASES_PHASE11]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE11 for item in case["questions"]]
    assert len(ids) == len(set(ids))
    assert len(stems) == len(set(stems))


def test_phase11_covers_required_refund_rules():
    sources = " ".join(
        item["source_ref"]
        for case in CURATED_GAP_CASES_PHASE11
        for item in case["questions"]
    )
    for article in ("854", "855", "857", "857-1", "858", "670"):
        assert article in sources
