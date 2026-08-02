from core.curated_gap_cases_phase15 import CURATED_GAP_CASES_PHASE15
from core.exam_format import is_official_functional_payload


def test_phase15_contains_three_complete_functional_gap_cases():
    assert len(CURATED_GAP_CASES_PHASE15) == 3
    assert sum(len(case["questions"]) for case in CURATED_GAP_CASES_PHASE15) == 9
    for case in CURATED_GAP_CASES_PHASE15:
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
        assert all(item["rationale"] for item in case["questions"])
        assert all(item["source_ref"] for item in case["questions"])


def test_phase15_ids_and_stems_are_unique():
    ids = [case["id"] for case in CURATED_GAP_CASES_PHASE15]
    stems = [item["stem"] for case in CURATED_GAP_CASES_PHASE15 for item in case["questions"]]
    assert len(ids) == len(set(ids))
    assert len(stems) == len(set(stems))


def test_phase15_covers_requested_evidence_flow_and_denfis_analysis():
    internal, external, denfis = CURATED_GAP_CASES_PHASE15

    assert "otra área o dependencia" in internal["questions"][0]["rationale"]
    assert "Auto Comisorio" in internal["questions"][1]["options"]["A"]
    assert "Acta de Diligencia" in internal["questions"][1]["options"]["A"]
    assert "dependencia solicitante" in internal["questions"][2]["options"]["A"]

    assert "Subdirección de Apoyo" in external["questions"][0]["options"]["A"]
    assert "claros, exactos y completos" in external["questions"][1]["options"]["A"]
    assert "debe continuar" in external["questions"][2]["options"]["A"]
    assert all("PR-COA-0223" in item["source_ref"] or "IN-COT-0083" in item["source_ref"] for item in external["questions"])

    assert "RUT" in denfis["questions"][0]["options"]["A"]
    assert "competencia" in denfis["questions"][1]["options"]["A"]
    assert "reserva" in denfis["questions"][2]["options"]["A"]
    assert "MN-COT-0043" in denfis["questions"][0]["source_ref"]
    assert "Resolución DIAN 67 de 2024" in denfis["questions"][2]["source_ref"]
