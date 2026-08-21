from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from core.learning.evidence_service import (
    ensure_question_revision,
    evaluate_opec_readiness,
    finalize_opec_session,
    record_opec_event,
    refresh_error_episode,
    start_opec_session,
)
from core.readiness_gate import ReadinessPolicy
from db.models import (
    Base,
    CaseOpecScope,
    CaseStudy,
    Competition,
    ErrorEpisode,
    OpecLearningEvent,
    OpecProfile,
    OpecTopicState,
    Question,
    QuestionCitation,
    QuestionOpecScope,
    QuestionRevision,
    SourceDocument,
    User,
    UserOPEC,
)


NOW = datetime(2026, 8, 15, 12, 0)


def _db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _verification():
    return {
        "status": "official_current",
        "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
        "locator": "Artículo 684",
        "supporting_excerpt": "La administración tiene amplias facultades de fiscalización.",
        "verified_on": "2026-08-15",
        "verified_by": "prueba editorial",
    }


def _context(db, *, with_profile=True):
    user = User(username="evidence-user", password_hash="x")
    competition = Competition(code="EVIDENCE", name="Evidence")
    db.add_all([user, competition])
    db.flush()
    user_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=[f"Función {number}" for number in range(1, 10)],
        is_active=True,
    )
    db.add(user_opec)
    db.flush()
    profile = None
    if with_profile:
        profile = OpecProfile(
            competition_id=competition.id,
            opec_number="236769",
            job_title="Gestor III",
            source_status="official_verified",
        )
        db.add(profile)
        db.flush()
    return user, competition, user_opec, profile


def _question(db, competition, profile, index, *, partition="training", likert=False):
    case = CaseStudy(
        id=f"case-{index}",
        competition_id=competition.id,
        title=f"OPEC 236769 F{(index % 9) + 1:02d}",
        text="La dependencia debe decidir con base en hechos y una regla vigente.",
        difficulty=2,
        topic="Fiscalización",
    )
    question = Question(
        question_id=f"question-{index}",
        competition_id=competition.id,
        case_id=case.id,
        track="COMPORTAMENTAL" if likert else "FUNCIONAL",
        competency="Trabajo en equipo" if likert else "Fiscalización",
        topic=f"OPEC 236769 F{(index % 9) + 1:02d} · Tema {index}",
        difficulty=2,
        question_type="LIKERT" if likert else "SITUATIONAL",
        stem="Actúo coordinadamente." if likert else "¿Cuál actuación está mejor sustentada?",
        options_json=(
            {"A": "Siempre", "B": "A veces", "C": "Casi nunca", "D": "Nunca"}
            if likert
            else {"A": "Aplicar la regla", "B": "Omitir controles", "C": "Delegar sin revisar"}
        ),
        correct_key=None if likert else "A",
        rationale="Aplicar la regla y documentar la decisión.",
        source_refs="Estatuto Tributario, artículo 684",
        is_verified=True,
        quality_report={
            "status": "APPROVED",
            "review": "source_grounded",
            "source_verification": _verification(),
        },
        hash_norm=f"question-hash-{index}",
    )
    db.add_all([case, question])
    db.flush()
    if profile is not None:
        function_number = (index % 9) + 1
        db.add_all([
            CaseOpecScope(
                case_id=case.id,
                opec_profile_id=profile.id,
                function_number=function_number,
            ),
            QuestionOpecScope(
                question_id=question.question_id,
                opec_profile_id=profile.id,
                function_number=function_number,
                bank_partition=partition,
            ),
        ])
        db.flush()
        source = db.query(SourceDocument).filter_by(document_key="test-et-684").first()
        if source is None:
            source = SourceDocument(
                document_key="test-et-684",
                title="Estatuto Tributario — fixture",
                entity="DIAN",
                document_type="estatuto",
                official_url=(
                    "https://normograma.dian.gov.co/dian/compilacion/"
                    "docs/estatuto_tributario.htm"
                ),
                validity_status="current",
                last_verified_at=NOW,
            )
            db.add(source)
            db.flush()
        db.add(QuestionCitation(
            question_id=question.question_id,
            source_document_id=source.id,
            locator="Artículo 684",
            excerpt="La administración tiene amplias facultades de fiscalización.",
            supports_key=True,
            verified_at=NOW,
            verified_by="prueba editorial",
        ))
        ensure_question_revision(db, question, bank_partition=partition)
        db.flush()
    return case, question


def test_training_event_uses_immutable_revision_topic_state_and_error():
    db = _db()
    user, competition, opec, profile = _context(db)
    _, question = _question(db, competition, profile, 0)

    session = start_opec_session(
        db,
        user_id=user.id,
        questions=[question],
        mode="training",
        bank_partition="training",
        now=NOW,
    )
    event_row = record_opec_event(
        db,
        session_id=session.id,
        user_id=user.id,
        question_id=question.question_id,
        chosen_key="B",
        confidence=None,
        time_sec=None,
        error_category="desconocimiento",
        user_reasoning="No recordé la facultad aplicable.",
        now=NOW + timedelta(minutes=1),
    )
    finished = finalize_opec_session(
        db, session_id=session.id, user_id=user.id, now=NOW + timedelta(minutes=2)
    )
    db.commit()

    assert finished.status == "completed"
    assert finished.score == 0
    assert event_row.confidence is None
    assert event_row.time_sec is None
    assert event_row.novelty == "new"
    assert event_row.editorial_difficulty == 5
    assert event_row.evidence_complete is True
    assert db.query(QuestionRevision).one().status == "approved"
    assert db.query(OpecTopicState).one().evidence_count == 1
    episode = db.query(ErrorEpisode).one()
    assert episode.category == "norm_unknown"
    assert episode.user_reasoning == "No recordé la facultad aplicable."
    assert episode.micro_lesson


def test_likert_is_saved_without_correctness_and_excluded_from_score():
    db = _db()
    user, competition, _, profile = _context(db)
    _, question = _question(db, competition, profile, 1, likert=True)
    session = start_opec_session(
        db,
        user_id=user.id,
        questions=[question],
        mode="training",
        bank_partition="training",
        now=NOW,
    )
    event_row = record_opec_event(
        db,
        session_id=session.id,
        user_id=user.id,
        question_id=question.question_id,
        chosen_key="A",
        confidence="high",
        now=NOW + timedelta(minutes=1),
    )
    finished = finalize_opec_session(
        db, session_id=session.id, user_id=user.id, now=NOW + timedelta(minutes=2)
    )
    assert event_row.is_correct is None
    assert finished.score is None
    assert db.query(OpecTopicState).count() == 0
    assert db.query(ErrorEpisode).count() == 0


def test_duplicate_event_and_opec_change_fail_closed():
    db = _db()
    user, competition, _, profile = _context(db)
    _, question = _question(db, competition, profile, 2)
    session = start_opec_session(
        db,
        user_id=user.id,
        questions=[question],
        mode="training",
        bank_partition="training",
        now=NOW,
    )
    record_opec_event(
        db,
        session_id=session.id,
        user_id=user.id,
        question_id=question.question_id,
        chosen_key="A",
        now=NOW + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="ya fue registrada"):
        record_opec_event(
            db,
            session_id=session.id,
            user_id=user.id,
            question_id=question.question_id,
            chosen_key="A",
        )

    db.query(UserOPEC).filter_by(user_id=user.id).update({UserOPEC.is_active: False})
    other = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="242699",
        job_title="Otro cargo",
        functions=[],
        is_active=True,
    )
    db.add(other)
    db.flush()
    with pytest.raises(ValueError, match="OPEC activa cambió"):
        finalize_opec_session(db, session_id=session.id, user_id=user.id)


def test_error_requires_two_delayed_novel_transfer_events_to_be_overcome():
    db = _db()
    user, competition, _, profile = _context(db)
    questions = [_question(db, competition, profile, index)[1] for index in range(3)]

    first = start_opec_session(
        db, user_id=user.id, questions=[questions[0]], mode="training",
        bank_partition="training", now=NOW,
    )
    record_opec_event(
        db, session_id=first.id, user_id=user.id,
        question_id=questions[0].question_id, chosen_key="B", now=NOW,
    )
    finalize_opec_session(db, session_id=first.id, user_id=user.id, now=NOW)
    episode = db.query(ErrorEpisode).one()

    for offset, question in enumerate(questions[1:], start=3):
        session = start_opec_session(
            db, user_id=user.id, questions=[question], mode="training",
            bank_partition="training", now=NOW + timedelta(days=offset),
        )
        record_opec_event(
            db, session_id=session.id, user_id=user.id,
            question_id=question.question_id, chosen_key="A", novelty="transfer",
            now=NOW + timedelta(days=offset),
        )
        finalize_opec_session(
            db, session_id=session.id, user_id=user.id,
            now=NOW + timedelta(days=offset),
        )

    refresh_error_episode(db, episode, now=NOW + timedelta(days=5))
    assert episode.status == "overcome"
    assert len(episode.reinforcement_question_ids) == 2
    assert episode.transfer_event_id is not None


def test_three_strict_measurements_feed_the_internal_85_gate():
    db = _db()
    user, competition, _, profile = _context(db)
    questions = [
        _question(db, competition, profile, index + 20, partition="measurement")[1]
        for index in range(3)
    ]
    policy = ReadinessPolicy(
        version="measurement-test-v1",
        target_score=85,
        required_sessions=3,
        minimum_functional_items_per_session=1,
        required_function_numbers=(3, 4, 5),
        max_session_age_days=30,
        minimum_retention_functional_items=1,
    )
    for index, question in enumerate(questions):
        started = NOW - timedelta(days=index + 1, minutes=5)
        completed = NOW - timedelta(days=index + 1)
        session = start_opec_session(
            db,
            user_id=user.id,
            questions=[question],
            mode="measurement",
            bank_partition="measurement",
            policy_version=policy.version,
            blueprint_version="measurement-blueprint-v1",
            feedback_enabled=False,
            aids_used=False,
            now=started,
        )
        record_opec_event(
            db,
            session_id=session.id,
            user_id=user.id,
            question_id=question.question_id,
            chosen_key="A",
            confidence=None,
            time_sec=None,
            now=completed,
        )
        finalize_opec_session(
            db, session_id=session.id, user_id=user.id, now=completed
        )
    db.commit()

    assessment = evaluate_opec_readiness(
        db, user_id=user.id, policy=policy, as_of=NOW
    )
    assert assessment.internal_precision_goal_met is True
    assert assessment.repeated_target_label == "meta interna repetida 3/3"
    assert assessment.official_result is None


def test_question_from_another_opec_is_rejected_even_in_same_competition():
    db = _db()
    user, competition, _, profile = _context(db)
    _, question = _question(db, competition, profile, 40)
    # Remove the explicit 236769 scope and declare another OPEC in metadata.
    db.query(QuestionOpecScope).filter_by(question_id=question.question_id).delete()
    report = dict(question.quality_report)
    report["scope"] = {"opec_number": "242699"}
    question.quality_report = report
    db.flush()
    with pytest.raises(ValueError, match="fuera del alcance OPEC"):
        start_opec_session(
            db,
            user_id=user.id,
            questions=[question],
            mode="training",
            bank_partition="training",
        )
