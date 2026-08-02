"""Repair macro-domain labels for all source-grounded OPEC 236769 cases."""

import argparse
import uuid
from collections import Counter

from core.curated_gap_cases import CURATED_GAP_CASES
from core.curated_gap_cases_phase2 import CURATED_GAP_CASES_PHASE2
from core.curated_gap_cases_phase3 import CURATED_GAP_CASES_PHASE3
from core.curated_gap_cases_phase4 import CURATED_GAP_CASES_PHASE4
from core.curated_gap_cases_phase5 import CURATED_GAP_CASES_PHASE5
from core.curated_gap_cases_phase6 import CURATED_GAP_CASES_PHASE6
from core.curated_gap_cases_phase7 import CURATED_GAP_CASES_PHASE7
from core.curated_gap_cases_phase8 import CURATED_GAP_CASES_PHASE8
from core.curated_gap_cases_phase9 import CURATED_GAP_CASES_PHASE9
from db.models import Question
from db.session import SessionLocal
from scripts.data.seed_curated_gap_cases_phase10_plus import PHASES_10_TO_16


ALL_CURATED_CASES = (
    CURATED_GAP_CASES
    + CURATED_GAP_CASES_PHASE2
    + CURATED_GAP_CASES_PHASE3
    + CURATED_GAP_CASES_PHASE4
    + CURATED_GAP_CASES_PHASE5
    + CURATED_GAP_CASES_PHASE6
    + CURATED_GAP_CASES_PHASE7
    + CURATED_GAP_CASES_PHASE8
    + CURATED_GAP_CASES_PHASE9
    + list(PHASES_10_TO_16)
)


def macro_domain(case: dict) -> str:
    case_id = case["id"]
    if any(
        token in case_id
        for token in (
            "cambiario",
            "prueba-interdependencia",
            "prueba-exterior",
        )
    ):
        return "Cambiario"
    if any(
        token in case_id
        for token in (
            "aduanas",
            "aduanero",
            "garantia",
            "apd",
            "contrabando",
            "f4-propuesta-apd",
            "ley2586",
        )
    ):
        return "Aduanero"
    if any(
        token in case_id
        for token in (
            "tributario",
            "liquidacion-provisional",
            "internacional",
            "pruebas-expediente",
            "pruebas-inspeccion",
            "devoluciones",
            "f9-revision",
        )
    ):
        return "Tributario"
    return "Transversal"


def repair(apply: bool = False) -> tuple[int, Counter]:
    db = SessionLocal()
    changed = 0
    counts = Counter()
    try:
        for case in ALL_CURATED_CASES:
            domain = macro_domain(case)
            case_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, case["id"]))
            questions = db.query(Question).filter(Question.case_id == case_uuid).all()
            counts[domain] += len(questions)
            for question in questions:
                if question.macro_dominio != domain:
                    question.macro_dominio = domain
                    changed += 1

        if apply:
            db.commit()
        else:
            db.rollback()
        return changed, counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changed, counts = repair(args.apply)
    mode = "APPLIED" if args.apply else "DRY RUN"
    summary = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    print(f"{mode}: changed={changed}; {summary}")
