"""Idempotently load reviewed GOA-style cases for OPEC 241130."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.curated_opec_241130 import CASE_SPECS, COMPETITION_CODE, questions_for_case
from core.dedupe import compute_hash
from db.models import CaseStudy, Competition, Question
from db.session import SessionLocal


def seed(apply: bool = False, db=None) -> tuple[int, int]:
    owned_session = db is None
    db = db or SessionLocal()
    cases_added = questions_added = 0
    try:
        competition = db.query(Competition).filter_by(code=COMPETITION_CODE).first()
        if competition is None:
            competition = Competition(
                code=COMPETITION_CODE,
                name="Territorial 12 - Gobernación de Bolívar",
                entity="Gobernación de Bolívar",
                is_active=True,
            )
            db.add(competition)
            db.flush()

        for case_index, spec in enumerate(CASE_SPECS):
            case_id = str(uuid.uuid5(uuid.NAMESPACE_URL, spec["id"]))
            case = db.get(CaseStudy, case_id)
            if case is None:
                case = CaseStudy(
                    id=case_id,
                    competition_id=competition.id,
                    title=f"OPEC 241130 F{spec['function']} - {spec['topic']}",
                    text=spec["text"],
                    topic=spec["topic"],
                    difficulty=spec["difficulty"],
                )
                db.add(case)
                cases_added += 1

            for item in questions_for_case(spec, case_index):
                hash_norm = compute_hash(item["stem"])
                question = db.query(Question).filter_by(hash_norm=hash_norm).first()
                if question is None:
                    question = Question(question_id=str(uuid.uuid4()), hash_norm=hash_norm)
                    db.add(question)
                    questions_added += 1
                question.competition_id = competition.id
                question.case_id = case_id
                question.track = "FUNCIONAL"
                question.competency = spec["topic"]
                question.topic = spec["topic"]
                question.macro_dominio = "Planeación territorial y gestión educativa"
                question.micro_competencia = f"OPEC 241130 F{spec['function']} · {spec['topic']}"
                question.difficulty = spec["difficulty"]
                question.question_type = "SITUATIONAL"
                question.stem = item["stem"]
                question.options_json = item["options"]
                question.correct_key = item["correct_key"]
                question.rationale = item["rationale"]
                question.source_refs = item["source_ref"]
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
        return cases_added, questions_added
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
    counts = seed(apply=args.apply)
    print(f"{'APPLIED' if args.apply else 'DRY RUN'}: {counts[0]} cases, {counts[1]} questions")
