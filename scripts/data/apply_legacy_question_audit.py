"""Attach the human legacy-bank audit without deleting questions or attempts."""

import argparse
import datetime

from core.legacy_question_audit import legacy_audit_decision
from db.models import Question
from db.session import SessionLocal


def apply_audit(apply: bool = False) -> dict[str, int]:
    db = SessionLocal()
    counts = {}
    try:
        questions = db.query(Question).filter(Question.is_verified.is_(True)).all()
        for question in questions:
            report = dict(question.quality_report or {})
            if report.get("review") == "human_source_grounded":
                continue
            decision, reason = legacy_audit_decision(question.topic or "")
            counts[decision] = counts.get(decision, 0) + 1
            report["legacy_audit"] = {
                "decision": decision,
                "reason": reason,
                "reviewed_by": "human_assisted_codex",
                "reviewed_at": datetime.date(2026, 8, 1).isoformat(),
            }
            question.quality_report = report
        if apply:
            db.commit()
        else:
            db.rollback()
        return counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(("APPLIED" if args.apply else "DRY RUN"), apply_audit(args.apply))
