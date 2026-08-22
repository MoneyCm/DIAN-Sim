"""Idempotently load curated OPEC 236769 phases 10 through 16."""

import argparse
import uuid

from core.curated_gap_cases_phase10 import CURATED_GAP_CASES_PHASE10
from core.curated_gap_cases_phase11 import CURATED_GAP_CASES_PHASE11
from core.curated_gap_cases_phase12 import CURATED_GAP_CASES_PHASE12
from core.curated_gap_cases_phase13 import CURATED_GAP_CASES_PHASE13
from core.curated_gap_cases_phase14 import CURATED_GAP_CASES_PHASE14
from core.curated_gap_cases_phase15 import CURATED_GAP_CASES_PHASE15
from core.curated_gap_cases_phase16 import CURATED_GAP_CASES_PHASE16
from core.dedupe import compute_hash
from core.opec_236769 import function_label
from db.models import CaseStudy, Competition, Question
from db.session import SessionLocal
from scripts.data.seed_curated_gap_cases import balanced_question


PHASES_10_TO_16 = (
    CURATED_GAP_CASES_PHASE10
    + CURATED_GAP_CASES_PHASE11
    + CURATED_GAP_CASES_PHASE12
    + CURATED_GAP_CASES_PHASE13
    + CURATED_GAP_CASES_PHASE14
    + CURATED_GAP_CASES_PHASE15
    + CURATED_GAP_CASES_PHASE16
)

COMPETITION_CODE = "DIAN-2676"


def dian_competition(db) -> Competition:
    """Resolve the target competition instead of relying on a database id."""
    competition = db.query(Competition).filter_by(code=COMPETITION_CODE).first()
    if competition is None:
        raise RuntimeError(f"No existe el concurso {COMPETITION_CODE}.")
    return competition


def macro_domain(case: dict) -> str:
    """Classify these reviewed cases by their real content, not one shared label."""
    case_id = case["id"]
    if "f4-propuesta-apd" in case_id:
        return "Aduanero"
    if "prueba-interdependencia" in case_id or "prueba-exterior" in case_id:
        return "Cambiario"
    if any(token in case_id for token in ("tributario", "devoluciones", "f9-revision")):
        return "Tributario"
    return "Transversal"


def seed(apply: bool = False) -> tuple[int, int]:
    db = SessionLocal()
    cases_added = questions_added = 0
    try:
        competition = dian_competition(db)
        for data in PHASES_10_TO_16:
            micro_competencia = function_label(data["id"], data["topic"])
            case_id = str(uuid.uuid5(uuid.NAMESPACE_URL, data["id"]))
            case = db.get(CaseStudy, case_id)
            if case is None:
                case = CaseStudy(
                    id=case_id,
                    competition_id=competition.id,
                    title=data["title"],
                    text=data["text"],
                    topic=data["topic"],
                    difficulty=data["difficulty"],
                )
                db.add(case)
                cases_added += 1
            else:
                case.title = data["title"]
                case.text = data["text"]
                case.topic = data["topic"]
                case.difficulty = data["difficulty"]

            domain = macro_domain(data)
            for index, item in enumerate(data["questions"]):
                options, correct_key = balanced_question(item, index)
                hash_norm = compute_hash(item["stem"])
                existing = db.query(Question).filter_by(hash_norm=hash_norm).first()
                if existing:
                    existing.case_id = case_id
                    existing.competition_id = competition.id
                    existing.options_json = options
                    existing.correct_key = correct_key
                    existing.rationale = item["rationale"]
                    existing.source_refs = item["source_ref"]
                    existing.macro_dominio = domain
                    existing.track = "FUNCIONAL"
                    existing.competency = data["topic"]
                    existing.topic = data["topic"]
                    existing.micro_competencia = micro_competencia
                    existing.difficulty = data["difficulty"]
                    existing.question_type = "SITUATIONAL"
                    existing.is_verified = True
                    existing.quality_report = {
                        "status": "APPROVED", "review": "human_source_grounded"
                    }
                    continue

                db.add(
                    Question(
                        question_id=str(uuid.uuid4()),
                        competition_id=competition.id,
                        case_id=case_id,
                        track="FUNCIONAL",
                        competency=data["topic"],
                        topic=data["topic"],
                        macro_dominio=domain,
                        micro_competencia=micro_competencia,
                        difficulty=data["difficulty"],
                        question_type="SITUATIONAL",
                        stem=item["stem"],
                        options_json=options,
                        correct_key=correct_key,
                        rationale=item["rationale"],
                        source_refs=item["source_ref"],
                        is_verified=True,
                        quality_report={
                            "status": "APPROVED",
                            "review": "human_source_grounded",
                        },
                        hash_norm=hash_norm,
                    )
                )
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
