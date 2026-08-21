"""Repair the 12 questions damaged by the 2026-08-20 option permutation.

Four questions can be restored from versioned source files. Eight questions
whose missing distractor cannot be recovered are quarantined, never deleted.
Every action creates an immutable candidate/quarantined revision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.learning.engine import editorial_question_difficulty
from core.question_revision import question_revision_hash
from db.models import OpecProfile, Question, QuestionOpecScope, QuestionRevision
from db.session import SessionLocal


MANIFEST_PATH = Path(__file__).resolve().parent / "manifest_2026-08-21_rotation_repair.json"
OPTION_KEYS = ("A", "B", "C")


def _clean_options(options) -> dict[str, str]:
    if not isinstance(options, dict) or set(options) != set(OPTION_KEYS):
        raise ValueError("La pregunta no tiene exactamente A, B y C.")
    clean = {key: str(options[key] or "").strip() for key in OPTION_KEYS}
    if any(not value for value in clean.values()) or len(set(clean.values())) != 3:
        raise ValueError("Las opciones objetivo deben ser completas y únicas.")
    return clean


def _add_revision(db, question, *, partition: str, status: str, reason: str) -> None:
    difficulty = editorial_question_difficulty(question)
    content_hash = question_revision_hash(question, difficulty)
    existing = db.query(QuestionRevision).filter_by(
        question_id=str(question.question_id),
        content_hash=content_hash,
        bank_partition=partition,
        status=status,
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
        bank_partition=partition,
        source_snapshot=dict(verification) if isinstance(verification, dict) else {},
        status=status,
        change_reason=reason,
        actor="rotation_repair_2026_08_21",
        actor_type="migration",
    ))


def _mark_report(question, *, status: str, reason: str, recovery_source: str = "") -> None:
    report = dict(question.quality_report or {})
    report.update(
        status=status,
        review="rotation_repair_pending_human_review",
        rotation_repair={
            "date": "2026-08-21",
            "reason": reason,
            "recovery_source": recovery_source,
        },
    )
    question.quality_report = report
    question.is_verified = False


def apply(dry_run: bool = False) -> tuple[int, int]:
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    changed = 0
    skipped = 0
    try:
        profile = db.query(OpecProfile).filter_by(opec_number="236769").first()
        if profile is None:
            raise RuntimeError("No existe el perfil canónico de la OPEC 236769.")

        for entry in entries:
            qid = str(entry["question_id"])
            question = db.get(Question, qid)
            scopes = db.query(QuestionOpecScope).filter_by(
                question_id=qid,
                opec_profile_id=profile.id,
            ).with_for_update().all()
            if question is None or len(scopes) != 1:
                raise RuntimeError(f"Pregunta o alcance ausente/duplicado: {qid}")
            scope = scopes[0]
            if scope.function_number != int(entry["function"]):
                raise RuntimeError(f"La función cambió para {qid}.")

            if entry["action"] == "repair_options":
                target_options = _clean_options(entry["target_options"])
                target_key = str(entry["target_key"])
                if scope.bank_partition != "training":
                    raise RuntimeError(f"La pregunta reparable ya no está en training: {qid}")
                if (
                    question.correct_key == target_key
                    and dict(question.options_json or {}) == target_options
                ):
                    _add_revision(
                        db,
                        question,
                        partition="training",
                        status="candidate",
                        reason="Opciones restauradas desde una fuente versionada; pendiente de revisión normativa.",
                    )
                    skipped += 1
                    continue
                current_values = [
                    str((question.options_json or {}).get(key, "")).strip()
                    for key in OPTION_KEYS
                ]
                if (
                    question.correct_key != entry["expected_current_key"]
                    or len(set(current_values)) != 2
                ):
                    raise RuntimeError(
                        f"El contenido de {qid} cambió; se evitó sobrescribir una edición posterior."
                    )
                if not dry_run:
                    question.options_json = target_options
                    question.correct_key = target_key
                    _mark_report(
                        question,
                        status="PENDING_HUMAN_REVIEW",
                        reason="Distractor restaurado tras rotación defectuosa.",
                        recovery_source=str(entry["recovery_source"]),
                    )
                    db.flush()
                    _add_revision(
                        db,
                        question,
                        partition="training",
                        status="candidate",
                        reason="Opciones restauradas desde una fuente versionada; pendiente de revisión normativa.",
                    )
                changed += 1
            elif entry["action"] == "quarantine":
                if scope.bank_partition == "reserved":
                    _add_revision(
                        db,
                        question,
                        partition="reserved",
                        status="quarantined",
                        reason=str(entry["reason"]),
                    )
                    skipped += 1
                    continue
                if scope.bank_partition != "training":
                    raise RuntimeError(f"Partición inesperada para {qid}: {scope.bank_partition}")
                if not dry_run:
                    scope.bank_partition = "reserved"
                    _mark_report(
                        question,
                        status="QUARANTINED",
                        reason=str(entry["reason"]),
                    )
                    db.flush()
                    _add_revision(
                        db,
                        question,
                        partition="reserved",
                        status="quarantined",
                        reason=str(entry["reason"]),
                    )
                changed += 1
            else:
                raise RuntimeError(f"Acción desconocida para {qid}: {entry['action']}")

        if dry_run:
            db.rollback()
        else:
            db.commit()
        print(f"Result: {changed} changed, {skipped} already correct")
        return changed, skipped
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    apply(dry_run="--dry-run" in sys.argv)
