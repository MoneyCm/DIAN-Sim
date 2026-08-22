"""Structural safeguards for the reviewed OPEC 236769 situational corpus."""

import re

from core.curated_gap_cases import CURATED_GAP_CASES
from core.curated_gap_cases_phase2 import CURATED_GAP_CASES_PHASE2
from core.curated_gap_cases_phase3 import CURATED_GAP_CASES_PHASE3
from core.curated_gap_cases_phase4 import CURATED_GAP_CASES_PHASE4
from core.curated_gap_cases_phase5 import CURATED_GAP_CASES_PHASE5
from core.curated_gap_cases_phase6 import CURATED_GAP_CASES_PHASE6
from core.curated_gap_cases_phase7 import CURATED_GAP_CASES_PHASE7
from core.curated_gap_cases_phase8 import CURATED_GAP_CASES_PHASE8
from core.curated_gap_cases_phase9 import CURATED_GAP_CASES_PHASE9
from core.curated_gap_cases_phase10 import CURATED_GAP_CASES_PHASE10
from core.curated_gap_cases_phase11 import CURATED_GAP_CASES_PHASE11
from core.curated_gap_cases_phase12 import CURATED_GAP_CASES_PHASE12
from core.curated_gap_cases_phase13 import CURATED_GAP_CASES_PHASE13
from core.curated_gap_cases_phase14 import CURATED_GAP_CASES_PHASE14
from core.curated_gap_cases_phase15 import CURATED_GAP_CASES_PHASE15
from core.curated_gap_cases_phase16 import CURATED_GAP_CASES_PHASE16
from core.opec_236769 import CASE_FUNCTIONS


CURATED_CASES = [
    case
    for batch in (
        CURATED_GAP_CASES, CURATED_GAP_CASES_PHASE2, CURATED_GAP_CASES_PHASE3,
        CURATED_GAP_CASES_PHASE4, CURATED_GAP_CASES_PHASE5, CURATED_GAP_CASES_PHASE6,
        CURATED_GAP_CASES_PHASE7, CURATED_GAP_CASES_PHASE8, CURATED_GAP_CASES_PHASE9,
        CURATED_GAP_CASES_PHASE10, CURATED_GAP_CASES_PHASE11, CURATED_GAP_CASES_PHASE12,
        CURATED_GAP_CASES_PHASE13, CURATED_GAP_CASES_PHASE14, CURATED_GAP_CASES_PHASE15,
        CURATED_GAP_CASES_PHASE16,
    )
    for case in batch
]


def test_opec236769_curated_cases_are_complete_and_mapped_to_the_manual():
    assert len(CURATED_CASES) == 48
    assert {case["id"] for case in CURATED_CASES} == set(CASE_FUNCTIONS)
    assert set(CASE_FUNCTIONS.values()) == set(range(1, 10))

    for case in CURATED_CASES:
        embedded_function = re.match(r"F(\d+)\s*-", case["topic"])
        if embedded_function:
            assert int(embedded_function.group(1)) == CASE_FUNCTIONS[case["id"]]
        assert len(case["text"].strip()) >= 80
        assert len(case["questions"]) == 3
        for question in case["questions"]:
            assert question["stem"].strip()
            assert set(question["options"]) == {"A", "B", "C"}
            assert question["correct_key"] in question["options"]
            assert question["rationale"].strip()
            assert question["source_ref"].strip()
