from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.curated_opec_241130 import CASE_SPECS, questions_for_case
from core.exam_format import build_official_case_blocks
from core.territorial12_bank import load_reviewed_questions
from db.models import Base, CaseStudy, Question
from scripts.data.seed_complete_opec241130 import seed as seed_complete_bank
from scripts.data.seed_curated_opec241130 import seed


def test_each_case_has_three_source_grounded_questions():
    assert len(CASE_SPECS) == 10
    assert set(item["function"] for item in CASE_SPECS) == set(range(1, 10))
    for index, spec in enumerate(CASE_SPECS):
        questions = questions_for_case(spec, index)
        assert len(questions) == 3
        assert all(question["source_ref"] and question["correct_key"] in "ABC" for question in questions)


def test_seed_creates_exam_ready_case_blocks():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    assert seed(apply=True, db=db) == (10, 30)
    cases = db.query(CaseStudy).all()
    assert len(build_official_case_blocks(cases)) == 10
    assert seed(apply=True, db=db) == (0, 0)


def test_complete_bank_has_100_reviewed_questions_and_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    assert len(load_reviewed_questions()) == 100
    created, total = seed_complete_bank(apply=True, db=db)
    assert (created, total) == (100, 100)
    assert db.query(Question).filter(Question.is_verified.is_(True)).count() == 100
    assert seed_complete_bank(apply=True, db=db) == (0, 100)
