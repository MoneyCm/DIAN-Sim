"""Apply the 2026-08-20 answer-key rotation without losing distractors.

Every changed question receives a candidate revision. The migration never
approves legal content; source verification and human approval remain separate.

Usage:
    python migrations/apply_rotation_2026-08-20.py [--dry-run]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.learning.engine import editorial_question_difficulty
from core.question_option_rotation import OptionRotationError, rotate_correct_option
from core.question_revision import question_revision_hash
from db.models import OpecProfile, Question, QuestionOpecScope, QuestionRevision
from db.session import SessionLocal


MANIFEST_PATH = Path(__file__).resolve().parent / "manifest_2026-08-20_rotation.json"
OPTION_KEYS = ("A", "B", "C")


def _options_are_unique(options) -> bool:
    if not isinstance(options, dict) or set(options) != set(OPTION_KEYS):
        return False
    values = [str(options.get(key, "")).strip() for key in OPTION_KEYS]
    return all(values) and len(values) == len(set(values))


def _add_candidate_revision(db, question: Question, *, bank_partition: str) -> None:
    difficulty = editorial_question_difficulty(question)
    content_hash = question_revision_hash(question, difficulty)
    existing = db.query(QuestionRevision).filter_by(
        question_id=str(question.question_id),
        content_hash=content_hash,
        bank_partition=bank_partition,
    ).first()
    if existing is not None:
        return

    next_number = int(
        db.query(func.max(QuestionRevision.revision_number))
        .filter(QuestionRevision.question_id == str(question.question_id))
        .scalar()
        or 0
    ) + 1
    report = question.quality_report if isinstance(question.quality_report, dict) else {}
    verification = report.get("source_verification")
    db.add(QuestionRevision(
        question_id=str(question.question_id),
        revision_number=next_number,
        content_hash=content_hash,
        stem=question.stem,
        options_json=dict(question.options_json or {}),
        correct_key=question.correct_key,
        rationale=question.rationale,
        difficulty_level=difficulty,
        bank_partition=bank_partition,
        source_snapshot=dict(verification) if isinstance(verification, dict) else {},
        status="candidate",
        change_reason="Rotación determinista de clave; pendiente de revisión normativa.",
        actor="migration_2026_08_20",
        actor_type="migration",
    ))


def apply(dry_run: bool = False) -> tuple[int, int, int]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    applied = 0
    skipped = 0
    errors = 0
    try:
        profile = db.query(OpecProfile).filter_by(opec_number="236769").first()
        if profile is None:
            raise RuntimeError("No existe el perfil canónico de la OPEC 236769.")

        for entry in manifest:
            if entry.get("action") != "reorder":
                continue

            qid = str(entry["question_id"])
            old_key = str(entry["old_key"])
            new_key = str(entry["new_key"])
            expected_partition = str(entry.get("partition", "training"))
            question = db.get(Question, qid)
            if question is None:
                print(f"  SKIP (not found): {qid[:12]}...")
                skipped += 1
                continue

            scopes = db.query(QuestionOpecScope).filter_by(
                question_id=qid,
                opec_profile_id=profile.id,
            ).all()
            if len(scopes) != 1 or scopes[0].function_number != int(entry["function"]):
                print(f"  ERROR (scope/function mismatch): {qid[:12]}")
                errors += 1
                continue
            if scopes[0].bank_partition != expected_partition:
                if (
                    scopes[0].bank_partition == "reserved"
                    and question.correct_key == new_key
                ):
                    print(f"  SKIP (superseded by later quarantine): {qid[:12]}...")
                    skipped += 1
                    continue
                print(f"  ERROR (partition mismatch): {qid[:12]}")
                errors += 1
                continue

            if question.correct_key == new_key:
                if not _options_are_unique(question.options_json):
                    print(f"  ERROR (already rotated but options are duplicated): {qid[:12]}")
                    errors += 1
                else:
                    print(f"  SKIP (already rotated): {qid[:12]}...")
                    skipped += 1
                continue
            if question.correct_key != old_key:
                print(f"  ERROR (key {question.correct_key}, expected {old_key}): {qid[:12]}")
                errors += 1
                continue

            try:
                rotated = rotate_correct_option(
                    question.options_json or {}, old_key=old_key, new_key=new_key
                )
            except OptionRotationError as exc:
                print(f"  ERROR ({exc}): {qid[:12]}")
                errors += 1
                continue

            if dry_run:
                print(f"  DRY-RUN Applied: {qid[:12]}... {old_key}->{new_key}")
                applied += 1
                continue

            question.options_json = rotated
            question.correct_key = new_key
            db.flush()
            _add_candidate_revision(db, question, bank_partition=expected_partition)
            applied += 1
            print(f"  Applied: {qid[:12]}... {old_key}->{new_key}")

        if dry_run:
            db.rollback()
        elif errors:
            db.rollback()
            raise RuntimeError(
                f"Migración cancelada: {errors} error(es); no se guardó ningún cambio."
            )
        else:
            db.commit()
        print(f"\nResult: {applied} applied, {skipped} skipped, {errors} errors")
        return applied, skipped, errors
    finally:
        db.close()


if __name__ == "__main__":
    is_dry_run = "--dry-run" in sys.argv
    if is_dry_run:
        print("=== DRY RUN ===\n")
    apply(dry_run=is_dry_run)
