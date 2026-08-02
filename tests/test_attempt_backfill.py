import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Attempt, Base, Question, QuestionPerformance, Skill, User
from services.attempt_backfill import backfill_attempt_performance


def test_backfill_recalculates_without_double_counting():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(username="backfill-user", password_hash="x", role="user")
    question = Question(
        question_id="backfill-q1", track="FUNCIONAL", competency="Tributario",
        topic="Prueba", stem="Caso", options_json={"A": "Sí", "B": "No"},
        correct_key="A", rationale="Regla", difficulty=1, hash_norm="backfill-hash",
    )
    db.add_all([user, question])
    db.flush()
    db.add_all([
        Attempt(question_id=question.question_id, user_id=user.id, chosen_key="A", is_correct=True,
                created_at=datetime.datetime(2026, 1, 1)),
        Attempt(question_id=question.question_id, user_id=user.id, chosen_key="B", is_correct=False,
                created_at=datetime.datetime(2026, 1, 2)),
    ])
    db.commit()

    first = backfill_attempt_performance(db, user.id)
    db.flush()
    second = backfill_attempt_performance(db, user.id)
    performance = db.query(QuestionPerformance).filter_by(user_id=user.id).one()
    skill = db.query(Skill).filter_by(user_id=user.id).one()
    assert first["created"] == 1
    assert second["created"] == 0
    assert (performance.hits, performance.misses) == (1, 1)
    assert performance.mastery_level == 5.0
    assert skill.mastery_score == 50.0
    assert skill.priority_weight == 2.0
    db.close()
