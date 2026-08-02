from core.curated_gap_cases_phase13 import CURATED_GAP_CASES_PHASE13
from core.exam_format import is_official_functional_payload


def test_phase13_contains_three_complete_notification_and_review_cases():
    assert len(CURATED_GAP_CASES_PHASE13) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE13) == 9
    for case in CURATED_GAP_CASES_PHASE13:
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
        assert all("Estatuto Tributario" in item["source_ref"] for item in case["questions"])
        assert all(item["rationale"] for item in case["questions"])
        assert all(item["correct_key"] == "A" for item in case["questions"])


def test_phase13_ids_and_stems_are_unique():
    ids = [case["id"] for case in CURATED_GAP_CASES_PHASE13]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE13 for item in case["questions"]]
    assert len(ids) == len(set(ids))
    assert len(stems) == len(set(stems))


def test_phase13_explicitly_corrects_the_legacy_electronic_notice_error():
    case = next(
        item
        for item in CURATED_GAP_CASES_PHASE13
        if item["id"] == "goa-236769-tributario-notificacion-electronica-01"
    )
    notification_question, term_question, _ = case["questions"]

    assert "fecha del envío" in notification_question["options"]["A"]
    assert "regla histórica del banco es incorrecta" in notification_question["rationale"]
    assert "cinco días" in term_question["options"]["A"]
    assert "sin confundir ese periodo con la fecha de notificación" in term_question["options"]["A"]
