from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.attempt_service import record_attempt
from db.models import Base, Competition, Question, QuestionPerformance, User


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    user = User(username="confidence-user", password_hash="x")
    competition = Competition(code="CONF", name="Confidence")
    db.add_all([user, competition])
    db.flush()
    question = Question(
        question_id="confidence-q",
        competition_id=competition.id,
        track="FUNCIONAL",
        competency="Aplicación",
        topic="Tema",
        difficulty=2,
        stem="Pregunta",
        options_json={"A": "Correcta", "B": "No", "C": "No"},
        correct_key="A",
        hash_norm="confidence-hash",
    )
    db.add(question)
    db.flush()
    return user, question


def test_missing_confidence_remains_unknown_in_telemetry():
    db = _db()
    user, question = _seed(db)
    record_attempt(
        db,
        user_id=user.id,
        question=question,
        chosen_key="B",
        confidence=None,
    )
    performance = db.query(QuestionPerformance).one()
    assert performance.last_confidence is None
    assert performance.next_review is not None


def test_declared_confidence_is_preserved_without_changing_correctness():
    db = _db()
    user, question = _seed(db)
    is_correct = record_attempt(
        db,
        user_id=user.id,
        question=question,
        chosen_key="B",
        confidence="confident",
    )
    performance = db.query(QuestionPerformance).one()
    assert is_correct is False
    assert performance.last_confidence == "confident"
