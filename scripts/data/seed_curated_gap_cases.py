"""Idempotently load human-reviewed OPEC 236769 cases."""

import argparse
import uuid

from core.curated_gap_cases import CURATED_GAP_CASES
from core.dedupe import compute_hash
from db.models import CaseStudy, Question
from db.session import SessionLocal


def seed(apply: bool = False) -> tuple[int, int]:
    db = SessionLocal()
    cases_added = questions_added = 0
    try:
        for data in CURATED_GAP_CASES:
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
            for item in data["questions"]:
                hash_norm = compute_hash(item["stem"])
                if db.query(Question).filter_by(hash_norm=hash_norm).first():
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
                    options_json=item["options"],
                    correct_key=item["correct_key"],
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
