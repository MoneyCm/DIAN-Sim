from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.learning.session_service import LearningSessionService
from db.models import (
    Base,
    Competition,
    LearningAttempt,
    LearningSession,
    Question,
    TopicMastery,
    User,
    UserOPEC,
)


def database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seeded_db():
    db = database()
    user = User(username="learner", email="learner@example.com", password_hash="x")
    competition = Competition(code="TEST", name="Concurso test", is_active=True)
    db.add_all([user, competition])
    db.flush()
    db.add(UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    ))
    for number, topic in enumerate(("Tema débil", "Tema fuerte"), start=1):
        db.add(Question(
            question_id=f"q{number}",
            competition_id=competition.id,
            track="FUNCIONAL",
            competency="Planeación",
            topic=topic,
            difficulty=2,
            stem=(
                f"Ante un hallazgo documentado en la actuación {number}, "
                "¿cuál es la decisión inicial más adecuada?"
            ),
            options_json={"A": "Correcta", "B": "Distractor", "C": "Distractor 2"},
            correct_key="A",
            rationale="La actuación correcta conserva trazabilidad y aplica la regla vigente.",
            source_refs="Fuente",
            is_verified=True,
            quality_report={
                "status": "APPROVED",
                "review": "source_grounded",
                "scope": {"opec_number": "236769"},
                "source_verification": {
                    "status": "official_current",
                    "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
                    "locator": "Artículo 684",
                    "supporting_excerpt": "La Administración Tributaria tiene amplias facultades de fiscalización.",
                    "verified_on": "2026-08-15",
                    "verified_by": "prueba editorial",
                },
            },
            hash_norm=f"hash-{number}",
        ))
    db.commit()
    return db, user.id, competition.id


def test_create_submit_and_finish_learning_session():
    db, user_id, competition_id = seeded_db()
    service = LearningSessionService(db)
    started_at = datetime(2026, 8, 6, 10, 0)
    session = service.start_learning_session(
        user_id=user_id, target_minutes=20, competition_id=competition_id, now=started_at
    )
    assert session.status == "active"
    assert session.question is not None

    outcome = service.submit_answer(
        session_id=session.session_id,
        user_id=user_id,
        answer="A",
        confidence="medium",
        response_time_seconds=12,
        now=started_at + timedelta(minutes=1),
    )
    assert outcome.evaluation.result.value == "correct"
    assert outcome.next_question is not None
    assert db.query(LearningAttempt).count() == 1
    mastery = db.query(TopicMastery).one()
    assert mastery.attempts == 1
    assert mastery.correct_attempts == 1
    assert mastery.next_review_at is not None

    finished = service.finish_session(
        session.session_id, user_id, now=started_at + timedelta(minutes=7)
    )
    assert finished.status == "completed"
    assert finished.actual_minutes == 7


def test_partial_result_is_persisted():
    db, user_id, competition_id = seeded_db()
    service = LearningSessionService(db)
    session = service.start_learning_session(
        user_id=user_id, target_minutes=10, competition_id=competition_id
    )
    outcome = service.submit_answer(
        session_id=session.session_id,
        user_id=user_id,
        answer="respuesta abierta",
        confidence="low",
        result_override="partial",
        error_type="application",
    )
    assert outcome.evaluation.result.value == "partial"
    assert outcome.evaluation.score == 0.6
    assert db.query(LearningAttempt).one().result == "partial"
    assert db.query(TopicMastery).one().partial_attempts == 1


def test_starting_new_session_abandons_previous_active_session():
    db, user_id, competition_id = seeded_db()
    service = LearningSessionService(db)
    first = service.start_learning_session(
        user_id=user_id, target_minutes=10, competition_id=competition_id
    )
    second = service.start_learning_session(
        user_id=user_id, target_minutes=15, competition_id=competition_id
    )
    assert first.session_id != second.session_id
    assert db.get(LearningSession, first.session_id).status == "abandoned"


def test_tutor_never_selects_another_opec_in_the_same_competition():
    db, user_id, competition_id = seeded_db()
    questions = db.query(Question).order_by(Question.question_id).all()
    questions[0].topic = "OPEC 236769 F01 · Tema"
    questions[0].micro_competencia = "OPEC 236769 F01 · Tema"
    questions[1].topic = "OPEC 242699 F01 · Tema"
    questions[1].micro_competencia = "OPEC 242699 F01 · Tema"
    second_report = dict(questions[1].quality_report)
    second_report["scope"] = {"opec_number": "242699"}
    questions[1].quality_report = second_report
    db.commit()

    session = LearningSessionService(db).start_learning_session(
        user_id=user_id, target_minutes=10, competition_id=competition_id
    )

    assert session.question.question_id == "q1"
