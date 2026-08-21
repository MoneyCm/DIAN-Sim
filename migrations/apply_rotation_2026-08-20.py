"""
Idempotent migration: apply rotation manifest to Neon DB.

Reads migrations/manifest_2026-08-20_rotation.json and applies each action
only if the question's current key still matches old_key. This makes the
migration safe to run multiple times.

Usage:
    python migrations/apply_rotation_2026-08-20.py [--dry-run]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.session import SessionLocal
from db.models import Question, QuestionOpecScope, OpecProfile


MANIFEST_PATH = Path(__file__).resolve().parent / "manifest_2026-08-20_rotation.json"


def apply(dry_run: bool = False):
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    db = SessionLocal()
    pid = db.query(OpecProfile).filter_by(opec_number="236769").first().id

    applied = 0
    skipped = 0
    errors = 0

    for entry in manifest:
        if entry.get("action") != "reorder":
            continue

        qid = entry["question_id"]
        old_key = entry["old_key"]
        new_key = entry["new_key"]

        q = db.query(Question).filter_by(question_id=qid).first()
        if not q:
            print(f"  SKIP (not found): {qid[:12]}...")
            skipped += 1
            continue

        if q.correct_key != old_key:
            print(f"  SKIP (key already {q.correct_key}, expected {old_key}): {qid[:12]}...")
            skipped += 1
            continue

        old_opts = dict(q.options_json or {})
        correct_text = old_opts.get(old_key)
        if not correct_text:
            print(f"  ERROR (missing option {old_key}): {qid[:12]}")
            errors += 1
            continue

        other_keys = [k for k in ["A", "B", "C"] if k != old_key and k != new_key]
        other_key = other_keys[0] if other_keys else None

        new_opts = {}
        for k in ["A", "B", "C"]:
            if k == new_key:
                new_opts[k] = correct_text
            elif k == old_key:
                new_opts[k] = old_opts.get(other_key, "")
            else:
                new_opts[k] = old_opts.get(k, "")

        if not dry_run:
            q.options_json = new_opts
            q.correct_key = new_key

        applied += 1
        print(f"  {'DRY-RUN ' if dry_run else ''}Applied: {qid[:12]}... {old_key}->{new_key} (F{entry['function']})")

    if not dry_run:
        db.commit()

    print(f"\nResult: {applied} applied, {skipped} skipped, {errors} errors")
    db.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN ===\n")
    apply(dry_run=dry_run)
