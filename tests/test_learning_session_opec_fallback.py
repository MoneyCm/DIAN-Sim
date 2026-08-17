from sqlalchemy import text

from core.learning.session_service import LearningSessionService


def test_opec_fallback_path_works_without_legacy_tables():
    # Reuse the same seeded DB fixture style as legacy tests.
    from tests.test_learning_session import seeded_db  # local import to avoid hard dependency

    db, user_id, competition_id = seeded_db()
    service = LearningSessionService(db)
    service._legacy_schema_available = False

    started = service.start_learning_session(
        user_id=user_id,
        target_minutes=10,
        competition_id=competition_id,
    )
    assert started.question is not None
    assert started.status == "active"
    assert started.session_id

    outcome = service.submit_answer(
        session_id=started.session_id,
        user_id=user_id,
        answer="A",
        confidence="medium",
        response_time_seconds=8,
    )
    assert outcome.next_question is not None

    finished = service.finish_session(started.session_id, user_id)
    assert finished.status == "completed"


def test_opec_fallback_handles_missing_topic_mastery_table():
    from tests.test_learning_session import seeded_db

    db, user_id, competition_id = seeded_db()
    db.execute(text("DROP TABLE topic_mastery"))
    db.commit()

    service = LearningSessionService(db)
    profile = service.learning_profile(user_id, competition_id)
    assert profile["general_mastery"] == 0.0

    started = service.start_learning_session(
        user_id=user_id,
        target_minutes=10,
        competition_id=competition_id,
    )
    assert started.status == "active"


def test_opec_fallback_handles_missing_learning_sessions_table():
    from tests.test_learning_session import seeded_db

    db, user_id, competition_id = seeded_db()
    db.execute(text("DROP TABLE learning_sessions"))
    db.commit()

    service = LearningSessionService(db)
    started = service.start_learning_session(
        user_id=user_id,
        target_minutes=10,
        competition_id=competition_id,
    )
    assert started.status == "active"


def test_opec_fallback_get_session_without_learning_sessions_table():
    from tests.test_learning_session import seeded_db

    db, user_id, competition_id = seeded_db()
    db.execute(text("DROP TABLE learning_sessions"))
    db.commit()

    service = LearningSessionService(db)
    service._legacy_schema_available = True
    started = service.start_learning_session(
        user_id=user_id,
        target_minutes=10,
        competition_id=competition_id,
    )
    assert started.status == "active"

    service._legacy_schema_available = True
    retrieved = service.get_session(started.session_id, user_id)
    assert retrieved is not None
    assert retrieved.session_id == started.session_id
    assert retrieved.question is not None


def test_opec_fallback_submit_answer_without_learning_sessions_table():
    from tests.test_learning_session import seeded_db

    db, user_id, competition_id = seeded_db()
    db.execute(text("DROP TABLE learning_sessions"))
    db.commit()

    service = LearningSessionService(db)
    service._legacy_schema_available = True
    started = service.start_learning_session(
        user_id=user_id,
        target_minutes=10,
        competition_id=competition_id,
    )
    assert started.status == "active"

    service._legacy_schema_available = True
    outcome = service.submit_answer(
        session_id=started.session_id,
        user_id=user_id,
        answer="A",
        confidence="medium",
        response_time_seconds=8,
    )
    assert outcome.evaluation.result.value in {"correct", "incorrect", "partial"}


def test_opec_fallback_finish_session_without_learning_sessions_table():
    from tests.test_learning_session import seeded_db

    db, user_id, competition_id = seeded_db()
    db.execute(text("DROP TABLE learning_sessions"))
    db.commit()

    service = LearningSessionService(db)
    service._legacy_schema_available = True
    started = service.start_learning_session(
        user_id=user_id,
        target_minutes=10,
        competition_id=competition_id,
    )
    assert started.status == "active"

    service._legacy_schema_available = True
    service.submit_answer(
        session_id=started.session_id,
        user_id=user_id,
        answer="A",
        confidence="medium",
        response_time_seconds=8,
    )

    service._legacy_schema_available = True
    finished = service.finish_session(started.session_id, user_id)
    assert finished.status == "completed"
