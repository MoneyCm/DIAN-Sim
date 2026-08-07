"""Completa el banco local de preguntas para Alimentación Escolar - UApA."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.question_banks.alimentacion_escolar import (
    COMPETITION_CODE,
    remove_obsolete_advanced_questions,
    seed_advanced_cases,
    seed_questions,
)
from db.models import Competition, Question
from db.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        competition = db.query(Competition).filter(Competition.code == COMPETITION_CODE).one()
        created = seed_questions(db, competition.id)
        advanced_created = seed_advanced_cases(db, competition.id)
        removed = remove_obsolete_advanced_questions(db, competition.id)
        total = db.query(Question).filter(Question.competition_id == competition.id).count()
        print(
            f"created={created} advanced_created={advanced_created} removed={removed} "
            f"total={total} competition_id={competition.id}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
