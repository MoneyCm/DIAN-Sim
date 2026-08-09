from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.curated_opec_241130 import CASE_SPECS, questions_for_case
from core.exam_format import build_official_case_blocks
from db.models import Base, CaseStudy
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
