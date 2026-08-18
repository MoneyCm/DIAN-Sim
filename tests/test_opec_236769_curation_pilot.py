import json
import uuid
from copy import deepcopy
from pathlib import Path

from core.dedupe import compute_hash
from core.question_content_fingerprint import (
    canonical_question_payload,
    compute_question_content_fingerprint,
)


PILOT_PATH = (
    Path(__file__).parents[1]
    / "data"
    / "opec_236769_curation_pilot_2026-08-15.json"
)


def _pilot():
    return json.loads(PILOT_PATH.read_text(encoding="utf-8"))


def test_full_content_fingerprint_is_canonical_but_content_sensitive():
    question = _pilot()["candidate_cases"][0]["questions"][0]
    reordered = deepcopy(question)
    reordered["options_json"] = json.dumps(
        {"C": question["options_json"]["C"], "A": question["options_json"]["A"], "B": question["options_json"]["B"]},
        ensure_ascii=False,
    )

    assert canonical_question_payload(reordered)["options_json"] == question["options_json"]
    assert compute_question_content_fingerprint(reordered) == question["content_fingerprint_sha256"]

    changed = deepcopy(question)
    changed["rationale"] += " Cambio material."
    assert compute_question_content_fingerprint(changed) != question["content_fingerprint_sha256"]

    moved = deepcopy(question)
    moved["case_id"] = str(uuid.uuid4())
    assert compute_question_content_fingerprint(moved) != question["content_fingerprint_sha256"]


def test_pilot_has_two_complete_source_grounded_pjs_rewrites():
    pilot = _pilot()

    assert pilot["activation_authorized"] is False
    assert pilot["snapshot"]["database_modified"] is False
    assert len(pilot["candidate_cases"]) == 2
    assert {case["function"]["number"] for case in pilot["candidate_cases"]} == {4, 8}

    for case in pilot["candidate_cases"]:
        assert case["case_id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, case["identity_seed"]))
        assert case["dictamen"] == "rewrite"
        assert case["candidate_disposition"] == "keep_after_independent_human_validation"
        assert case["case_length_chars"] == len(case["scenario"])
        assert 450 <= len(case["scenario"]) <= 700
        assert len(case["questions"]) == 3

        for question in case["questions"]:
            assert question["question_id"] == str(
                uuid.uuid5(uuid.NAMESPACE_URL, question["identity_seed"])
            )
            assert question["case_id"] == case["case_id"]
            assert question["stem_length_chars"] == len(question["stem"])
            assert 150 <= len(question["stem"]) <= 250
            assert set(question["options_json"]) == {"A", "B", "C"}
            assert question["correct_key"] in question["options_json"]
            assert question["option_length_chars"] == {
                key: len(value) for key, value in question["options_json"].items()
            }
            assert all(80 <= len(value) <= 120 for value in question["options_json"].values())
            assert question["hash_norm"] == compute_hash(question["stem"])
            assert question["content_fingerprint_sha256"] == compute_question_content_fingerprint(question)
            assert question["evidence"]["url"].startswith(
                "https://normograma.dian.gov.co/"
            )
            assert question["evidence"]["consulted_on"] == "2026-08-15"
            assert question["evidence"]["locator"].startswith("artículo ")
            assert question["dictamen"] == "keep"
            assert question["db_approved"] is False


def test_snapshot_items_are_traceability_only_and_marked_for_rewrite():
    pilot = _pilot()

    assert len(pilot["source_snapshot_assessment"]) == 2
    assert all(
        case["dictamen"] == "rewrite"
        for case in pilot["source_snapshot_assessment"]
    )
    assert all(
        question["dictamen"] == "rewrite"
        for case in pilot["source_snapshot_assessment"]
        for question in case["questions"]
    )
    assert all(
        len(question_id) == 36
        for case in pilot["candidate_cases"]
        for question in case["questions"]
        for question_id in question["source_question_ids"]
    )
