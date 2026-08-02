"""Idempotently load human-reviewed OPEC 236769 cases."""

import argparse
import uuid

from core.curated_gap_cases import CURATED_GAP_CASES
from core.curated_gap_cases_phase2 import CURATED_GAP_CASES_PHASE2
from core.curated_gap_cases_phase3 import CURATED_GAP_CASES_PHASE3
from core.curated_gap_cases_phase4 import CURATED_GAP_CASES_PHASE4
from core.curated_gap_cases_phase5 import CURATED_GAP_CASES_PHASE5
from core.curated_gap_cases_phase6 import CURATED_GAP_CASES_PHASE6
from core.curated_gap_cases_phase7 import CURATED_GAP_CASES_PHASE7
from core.curated_gap_cases_phase8 import CURATED_GAP_CASES_PHASE8
from core.dedupe import compute_hash
from db.models import CaseStudy, Question
from db.session import SessionLocal


def balanced_question(item: dict, index: int) -> tuple[dict, str]:
    """Rotate options so every case has one A, one B and one C key."""
    target = ("A", "B", "C")[index]
    options = item["options"]
    correct_text = options[item["correct_key"]]
    wrong = [text for key, text in options.items() if key != item["correct_key"]]
    rotated = {}
    wrong_index = 0
    for key in ("A", "B", "C"):
        if key == target:
            rotated[key] = correct_text
        else:
            rotated[key] = wrong[wrong_index]
            wrong_index += 1
    return rotated, target


def seed(apply: bool = False) -> tuple[int, int]:
    db = SessionLocal()
    cases_added = questions_added = 0
    try:
        all_cases = (
            CURATED_GAP_CASES
            + CURATED_GAP_CASES_PHASE2
            + CURATED_GAP_CASES_PHASE3
            + CURATED_GAP_CASES_PHASE4
            + CURATED_GAP_CASES_PHASE5
            + CURATED_GAP_CASES_PHASE6
            + CURATED_GAP_CASES_PHASE7
            + CURATED_GAP_CASES_PHASE8
        )
        for data in all_cases:
            case_id = str(uuid.uuid5(uuid.NAMESPACE_URL, data["id"]))
            case = db.get(CaseStudy, case_id)
            if case is None:
                case = CaseStudy(
                    id=case_id,
                    competition_id=1,
                    title=data["title"],
                    text=data["text"],
                    topic=data["topic"],
                    difficulty=data["difficulty"],
                )
                db.add(case)
                cases_added += 1
            for index, item in enumerate(data["questions"]):
                options, correct_key = balanced_question(item, index)
                hash_norm = compute_hash(item["stem"])
                existing = db.query(Question).filter_by(hash_norm=hash_norm).first()
                if existing:
                    existing.options_json = options
                    existing.correct_key = correct_key
                    existing.rationale = item["rationale"]
                    existing.source_refs = item["source_ref"]
                    existing.is_verified = True
                    continue
                db.add(Question(
                    question_id=str(uuid.uuid4()),
                    competition_id=1,
                    case_id=case_id,
                    track="FUNCIONAL",
                    competency=data["topic"],
                    topic=data["topic"],
                    macro_dominio="Fiscalización y liquidación",
                    micro_competencia=data["topic"],
                    difficulty=data["difficulty"],
                    question_type="SITUATIONAL",
                    stem=item["stem"],
                    options_json=options,
                    correct_key=correct_key,
                    rationale=item["rationale"],
                    source_refs=item["source_ref"],
                    is_verified=True,
                    quality_report={"status": "APPROVED", "review": "human_source_grounded"},
                    hash_norm=hash_norm,
                ))
                questions_added += 1
        if apply:
            db.commit()
        else:
            db.rollback()
        return cases_added, questions_added
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    counts = seed(args.apply)
    print(f"{'APPLIED' if args.apply else 'DRY RUN'}: {counts[0]} cases, {counts[1]} questions")
