"""Idempotently load the complete reviewed study bank for OPEC 241130."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.dedupe import compute_hash
from core.territorial12_bank import load_reviewed_questions
from db.models import Competition, Question
from db.session import SessionLocal


COMPETITION_CODE = "TERRITORIAL-12-BOLIVAR-2685"


def seed(apply: bool = False, db=None) -> tuple[int, int]:
    """Load or repair all 100 reviewed questions and return created/total counts."""
    owned_session = db is None
    db = db or SessionLocal()
    created = 0
    try:
        competition = db.query(Competition).filter_by(code=COMPETITION_CODE).first()
        if competition is None:
            competition = Competition(
                code=COMPETITION_CODE,
                name="Territorial 12 - Gobernación de Bolívar",
                entity="Gobernación de Bolívar",
                description="Proceso de Selección Territorial 12, OPEC 241130.",
                is_active=True,
            )
            db.add(competition)
            db.flush()

        for stem, options, correct_key, rationale, source_ref in load_reviewed_questions():
            question = (
                db.query(Question)
                .filter(Question.competition_id == competition.id, Question.stem == stem)
                .first()
            )
            if question is None:
                question = Question(
                    question_id=str(uuid.uuid4()),
                    hash_norm=compute_hash(f"{COMPETITION_CODE}|{stem}"),
                )
                db.add(question)
                created += 1
            question.competition_id = competition.id
            question.track = "FUNCIONAL"
            question.competency = "Planeación y gestión pública"
            question.topic = "Territorial 12 - Bolívar"
            question.macro_dominio = "Planeación territorial"
            question.micro_competencia = "Planeación, seguimiento y evaluación"
            question.difficulty = 2
            question.question_type = "SITUATIONAL"
            question.stem = stem
            question.options_json = options
            question.correct_key = correct_key
            question.rationale = rationale
            question.source_refs = source_ref
            question.is_verified = True
            question.quality_report = {
                "status": "APPROVED",
                "review": "human_source_grounded",
                "source_version": "cnsc-2025-11-27",
                "opec": "241130",
            }

        if apply:
            db.commit()
        else:
            db.rollback()
        total = db.query(Question).filter(Question.competition_id == competition.id).count()
        return created, total
    except Exception:
        db.rollback()
        raise
    finally:
        if owned_session:
            db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    created, total = seed(apply=args.apply)
    print(f"{'APPLIED' if args.apply else 'DRY RUN'}: {created} nuevas, {total} totales")
