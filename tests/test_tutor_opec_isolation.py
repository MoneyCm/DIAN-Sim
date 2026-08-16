from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.learning.engine import topic_id_for
from core.learning.session_service import LearningSessionService
from db.models import (
    Base,
    Competition,
    LearningAttempt,
    LearningSession,
    OpecLearningEvent,
    OpecLearningSession,
    OpecTopicState,
    Question,
    TopicMastery,
    User,
    UserOPEC,
)


def _quality(opec_number: str) -> dict:
    return {
        "status": "APPROVED",
        "review": "source_grounded",
        "scope": {"opec_number": opec_number},
        "source_verification": {
            "status": "official_current",
            "url": (
                "https://normograma.dian.gov.co/dian/compilacion/"
                "docs/estatuto_tributario.htm"
            ),
            "locator": "Artículo 684",
            "supporting_excerpt": (
                "La Administración Tributaria tiene amplias facultades "
                "de fiscalización e investigación."
            ),
            "verified_on": "2026-08-15",
            "verified_by": "prueba editorial",
        },
    }


def _database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(username="tutor", email="tutor@example.com", password_hash="x")
    competition = Competition(code="SHARED", name="Concurso compartido", is_active=True)
    db.add_all([user, competition])
    db.flush()
    opec_a = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Fiscalizar"],
        is_active=True,
    )
    opec_b = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="242699",
        job_title="Analista",
        functions=["Analizar"],
        is_active=False,
    )
    db.add_all([opec_a, opec_b])
    db.flush()
    for question_id, opec_number in (("q-a", "236769"), ("q-b", "242699")):
        db.add(Question(
            question_id=question_id,
            competition_id=competition.id,
            track="FUNCIONAL",
            competency="Fiscalización",
            topic="Tema compartido",
            micro_competencia=f"OPEC {opec_number} F01",
            difficulty=2,
            stem=f"SITUACIÓN OPEC {opec_number}: ¿qué actuación corresponde?",
            options_json={"A": "Correcta", "B": "Distractor", "C": "Distractor 2"},
            correct_key="A",
            rationale="Aplicar la regla verificada.",
            source_refs="Estatuto Tributario, artículo 684",
            is_verified=True,
            quality_report=_quality(opec_number),
            hash_norm=f"hash-{question_id}",
        ))
    db.commit()
    return db, user, competition, opec_a, opec_b


def _switch_opec(db, old: UserOPEC, new: UserOPEC) -> None:
    old.is_active = False
    new.is_active = True
    db.commit()


def test_tutor_persists_canonical_session_and_event_in_exact_opec():
    db, user, competition, opec_a, _opec_b = _database()
    service = LearningSessionService(db)
    started = service.start_learning_session(
        user_id=user.id,
        target_minutes=10,
        competition_id=competition.id,
        now=datetime(2026, 8, 15, 10, 0),
    )

    assert started.question.question_id == "q-a"
    canonical = db.query(OpecLearningSession).one()
    assert canonical.user_opec_id == opec_a.id
    assert canonical.opec_number == "236769"
    assert canonical.coverage["legacy_session_id"] == started.session_id
    assert canonical.coverage["question_ids"] == ["q-a"]

    service.submit_answer(
        session_id=started.session_id,
        user_id=user.id,
        answer="A",
        confidence="high",
        response_time_seconds=9,
        now=datetime(2026, 8, 15, 10, 1),
    )

    event = db.query(OpecLearningEvent).one()
    assert event.session_id == canonical.id
    assert event.question_id == "q-a"
    assert event.confidence == "high"
    assert event.time_sec == 9
    state = db.query(OpecTopicState).one()
    assert state.user_opec_id == opec_a.id
    assert state.evidence_count == 1


def test_changing_opec_invalidates_old_tutor_session_before_display_or_reuse():
    db, user, competition, opec_a, opec_b = _database()
    service = LearningSessionService(db)
    first = service.start_learning_session(
        user_id=user.id,
        target_minutes=10,
        competition_id=competition.id,
    )
    _switch_opec(db, opec_a, opec_b)

    stale = service.get_session(first.session_id, user.id)

    assert stale.status == "abandoned"
    assert stale.question is None
    assert db.get(LearningSession, first.session_id).status == "abandoned"
    assert db.query(OpecLearningSession).one().status == "invalid"

    second = service.start_learning_session(
        user_id=user.id,
        target_minutes=10,
        competition_id=competition.id,
    )
    assert second.question.question_id == "q-b"
    canonical = (
        db.query(OpecLearningSession)
        .filter(OpecLearningSession.status == "active")
        .one()
    )
    assert canonical.user_opec_id == opec_b.id


def test_tampered_cross_opec_question_is_neither_shown_nor_recorded():
    db, user, competition, _opec_a, _opec_b = _database()
    service = LearningSessionService(db)
    started = service.start_learning_session(
        user_id=user.id,
        target_minutes=10,
        competition_id=competition.id,
    )
    legacy = db.get(LearningSession, started.session_id)
    legacy.current_question_id = "q-b"
    db.commit()

    with pytest.raises(ValueError, match="OPEC activa cambió"):
        service.submit_answer(
            session_id=started.session_id,
            user_id=user.id,
            answer="A",
            confidence="medium",
        )

    assert db.query(LearningAttempt).count() == 0
    assert db.query(OpecLearningEvent).count() == 0
    assert db.get(LearningSession, started.session_id).status == "abandoned"


def test_profile_and_evolution_prefer_canonical_state_scoped_by_opec():
    db, user, competition, opec_a, opec_b = _database()
    service = LearningSessionService(db)
    started = service.start_learning_session(
        user_id=user.id,
        target_minutes=10,
        competition_id=competition.id,
    )
    service.submit_answer(
        session_id=started.session_id,
        user_id=user.id,
        answer="A",
        confidence="medium",
    )
    topic_id = topic_id_for("FUNCIONAL", "Fiscalización", "Tema compartido")
    legacy_state = db.query(TopicMastery).filter_by(
        user_id=user.id,
        competition_id=competition.id,
        topic_id=topic_id,
    ).one()
    legacy_state.mastery_score = 99.0
    legacy_state.attempts = 99
    db.commit()

    profile_a = service.learning_profile(user.id, competition.id)
    assert profile_a["general_mastery"] == 20.0
    assert profile_a["topics"][0].attempts == 1
    assert len(service.recent_evolution(user.id, competition.id)) == 1

    _switch_opec(db, opec_a, opec_b)
    db.add(OpecTopicState(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=opec_b.id,
        opec_number=opec_b.opec_number,
        topic_id=topic_id,
        topic_label="Tema compartido",
        mastery_score=80.0,
        evidence_count=4,
    ))
    db.commit()

    profile_b = service.learning_profile(user.id, competition.id)
    assert profile_b["general_mastery"] == 80.0
    assert profile_b["topics"][0].attempts == 4
    assert service.recent_evolution(user.id, competition.id) == []


def test_tutor_does_not_infer_missing_confidence():
    db, user, competition, _opec_a, _opec_b = _database()
    service = LearningSessionService(db)
    started = service.start_learning_session(
        user_id=user.id,
        target_minutes=10,
        competition_id=competition.id,
    )

    with pytest.raises(ValueError, match="Declara tu nivel de confianza"):
        service.submit_answer(
            session_id=started.session_id,
            user_id=user.id,
            answer="A",
            confidence=None,
        )

    assert db.query(LearningAttempt).count() == 0
    assert db.query(OpecLearningEvent).count() == 0
