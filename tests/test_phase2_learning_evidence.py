import datetime

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base,
    CaseStudy,
    Competition,
    ErrorEpisode,
    OpecLearningEvent,
    OpecLearningSession,
    OpecStudyPlan,
    OpecTopicState,
    Question,
    QuestionRevision,
    SourceDocument,
    StudyActivity,
    User,
    UserOPEC,
)
from scripts.migrations.phase2_learning_evidence import (
    PHASE2_TABLES,
    PreflightError,
    migrate,
)


NOW = datetime.datetime(2026, 8, 15, 12, 0)


def _engine(url="sqlite:///:memory:"):
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def _foreign_keys_on(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _database():
    engine = _engine()
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)()


def _seed(db):
    user = User(
        username="phase2-user",
        password_hash="x",
        role="user",
        subscription_tier="free",
    )
    competition = Competition(code="PHASE2", name="Concurso Fase 2")
    db.add_all([user, competition])
    db.flush()
    first_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=[],
        is_active=True,
    )
    second_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="242699",
        job_title="Analista I",
        functions=[],
        is_active=False,
    )
    case = CaseStudy(
        competition_id=competition.id,
        title="Caso",
        text="Situación laboral",
        difficulty=5,
        topic="Fiscalización",
    )
    source = SourceDocument(
        document_key="estatuto-phase2",
        title="Estatuto Tributario",
        official_url="https://normograma.dian.gov.co/",
        validity_status="current",
    )
    db.add_all([first_opec, second_opec, case, source])
    db.flush()
    question = Question(
        question_id="phase2-likert",
        competition_id=competition.id,
        case_id=case.id,
        track="COMPORTAMENTAL",
        competency="Trabajo en equipo",
        topic="Colaboración",
        difficulty=2,
        question_type="LIKERT",
        stem="Prefiero coordinar antes de actuar.",
        options_json={"A": "Siempre", "B": "A veces", "C": "Nunca"},
        correct_key=None,
        rationale="Ítem de autorreporte sin clave correcta.",
        source_refs="Decreto 815 de 2018",
        is_verified=True,
        hash_norm="phase2-likert-hash",
    )
    db.add(question)
    db.flush()
    revision = QuestionRevision(
        question_id=question.question_id,
        revision_number=1,
        content_hash="revision-hash",
        stem=question.stem,
        options_json=question.options_json,
        correct_key=None,
        difficulty_level=5,
        bank_partition="training",
        status="approved",
    )
    db.add(revision)
    db.commit()
    return user, competition, first_opec, second_opec, case, question, revision, source


def _learning_session(db, user, competition, user_opec, *, total=1, answered=0):
    row = OpecLearningSession(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=user_opec.id,
        opec_number=user_opec.opec_number,
        mode="diagnostic",
        policy_version="phase2-v1",
        blueprint_version="opec-236769-v1",
        bank_partition="training",
        status="active",
        started_at=NOW,
        total_questions=total,
        answered_questions=answered,
        feedback_enabled=False,
        aids_used=False,
        question_revision_ids=[],
        case_ids=[],
        coverage={"functions": [1]},
    )
    db.add(row)
    db.flush()
    return row


def _learning_event(
    db,
    session,
    user,
    question,
    revision,
    case,
    *,
    is_correct=None,
    time_sec=None,
    novelty="new",
    difficulty=5,
    created_at=NOW,
):
    row = OpecLearningEvent(
        session_id=session.id,
        user_id=user.id,
        question_id=question.question_id,
        case_id=case.id,
        question_revision_id=revision.id,
        function_number=1,
        topic_id="topic-collaboration",
        topic_label="Colaboración",
        is_correct=is_correct,
        confidence=None,
        time_sec=time_sec,
        novelty=novelty,
        editorial_difficulty=difficulty,
        source_verified=True,
        source_current=True,
        evidence_complete=True,
        created_at=created_at,
    )
    db.add(row)
    db.flush()
    return row


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "practice"},
        {"total_questions": 1, "answered_questions": 2},
        {"score": 101},
        {"bank_partition": "unscoped"},
        {"status": "completed", "completed_at": None},
    ],
)
def test_learning_session_constraints_reject_invalid_values(changes):
    _, db = _database()
    user, competition, first, _, _, _, _, _ = _seed(db)

    invalid = _learning_session(db, user, competition, first)
    for field, value in changes.items():
        setattr(invalid, field, value)
    with pytest.raises(IntegrityError):
        db.commit()


def test_likert_event_preserves_null_correctness_and_null_time():
    _, db = _database()
    user, competition, first, _, case, question, revision, _ = _seed(db)
    session = _learning_session(db, user, competition, first, answered=1)
    event_row = _learning_event(
        db, session, user, question, revision, case,
        is_correct=None, time_sec=None,
    )
    db.commit()

    stored = db.get(OpecLearningEvent, event_row.id)
    assert stored.is_correct is None
    assert stored.time_sec is None
    assert stored.editorial_difficulty == 5


@pytest.mark.parametrize(
    ("time_sec", "difficulty"),
    [(-1, 5), (10, 0), (10, 11)],
)
def test_learning_event_rejects_negative_time_and_out_of_range_difficulty(
    time_sec, difficulty
):
    _, db = _database()
    user, competition, first, _, case, question, revision, _ = _seed(db)
    session = _learning_session(db, user, competition, first, answered=1)
    db.add(OpecLearningEvent(
        session_id=session.id,
        user_id=user.id,
        question_id=question.question_id,
        case_id=case.id,
        question_revision_id=revision.id,
        function_number=1,
        topic_id="topic-collaboration",
        topic_label="Colaboración",
        is_correct=None,
        time_sec=time_sec,
        novelty="new",
        editorial_difficulty=difficulty,
        source_verified=True,
        source_current=True,
        evidence_complete=True,
        created_at=NOW,
    ))
    with pytest.raises(IntegrityError):
        db.commit()


def test_topic_state_is_isolated_by_configured_opec():
    _, db = _database()
    user, competition, first, second, _, _, _, _ = _seed(db)
    for user_opec, score in ((first, 25), (second, 90)):
        db.add(OpecTopicState(
            user_id=user.id,
            competition_id=competition.id,
            user_opec_id=user_opec.id,
            opec_number=user_opec.opec_number,
            topic_id="shared-topic",
            topic_label="Tema con el mismo nombre",
            mastery_score=score,
        ))
    db.commit()

    rows = db.query(OpecTopicState).order_by(OpecTopicState.mastery_score).all()
    assert [(row.opec_number, row.mastery_score) for row in rows] == [
        ("236769", 25),
        ("242699", 90),
    ]

    db.add(OpecTopicState(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=first.id,
        opec_number=first.opec_number,
        topic_id="shared-topic",
        topic_label="Duplicado",
        mastery_score=50,
    ))
    with pytest.raises(IntegrityError):
        db.commit()


def test_error_can_be_overcome_only_with_a_distinct_transfer_event():
    _, db = _database()
    user, competition, first, _, case, question, revision, _ = _seed(db)
    session = _learning_session(db, user, competition, first, total=2, answered=2)
    failed = _learning_event(
        db, session, user, question, revision, case,
        is_correct=False, time_sec=45, novelty="new",
    )
    transfer_question = Question(
        question_id="phase2-transfer",
        competition_id=competition.id,
        case_id=case.id,
        track="FUNCIONAL",
        competency="Fiscalización",
        topic="Excepciones",
        difficulty=6,
        question_type="SITUATIONAL",
        stem="¿Qué excepción se aplica en el nuevo caso?",
        options_json={"A": "La excepción acreditada", "B": "La regla general", "C": "Ninguna"},
        correct_key="A",
        rationale="La evidencia del caso activa la excepción.",
        source_refs="Estatuto Tributario, artículo 1",
        is_verified=True,
        hash_norm="phase2-transfer-hash",
    )
    db.add(transfer_question)
    db.flush()
    transfer_revision = QuestionRevision(
        question_id=transfer_question.question_id,
        revision_number=1,
        content_hash="phase2-transfer-revision",
        stem=transfer_question.stem,
        options_json=transfer_question.options_json,
        correct_key="A",
        difficulty_level=6,
        bank_partition="training",
        status="approved",
    )
    db.add(transfer_revision)
    db.flush()
    transfer = _learning_event(
        db, session, user, transfer_question, transfer_revision, case,
        is_correct=True, time_sec=30, novelty="transfer",
        created_at=NOW + datetime.timedelta(days=7),
    )
    db.commit()

    db.add(ErrorEpisode(
        learning_event_id=failed.id,
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=first.id,
        opec_number=first.opec_number,
        question_id=question.question_id,
        question_revision_id=revision.id,
        category="missed_exception",
        status="overcome",
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    episode = ErrorEpisode(
        learning_event_id=failed.id,
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=first.id,
        opec_number=first.opec_number,
        question_id=question.question_id,
        question_revision_id=revision.id,
        category="missed_exception",
        user_reasoning="No identifiqué la excepción temporal.",
        rule_to_remember="Comprobar siempre regla y excepción aplicable.",
        source_reference={"document": "Estatuto", "locator": "Artículo 1"},
        micro_lesson="Contrasta el supuesto general con sus excepciones.",
        status="overcome",
        transfer_event_id=transfer.id,
        transfer_evidence={"novelty": "transfer", "correct": True},
        overcome_at=NOW + datetime.timedelta(days=7),
    )
    db.add(episode)
    db.commit()
    assert episode.transfer_event_id == transfer.id
    assert transfer.question_id != failed.question_id


def test_study_plan_is_unique_per_opec_and_activity_is_source_linked():
    _, db = _database()
    user, competition, first, second, _, _, _, source = _seed(db)
    first_plan = OpecStudyPlan(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=first.id,
        opec_number=first.opec_number,
        exam_date=datetime.date(2026, 12, 15),
        weekday_minutes=30,
        saturday_minutes=60,
        study_days=[0, 1, 2, 3, 4, 5],
        policy_version="phase2-v1",
    )
    second_plan = OpecStudyPlan(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=second.id,
        opec_number=second.opec_number,
        target_score=90,
        weekday_minutes=45,
        saturday_minutes=90,
        study_days=[0, 2, 5],
        policy_version="phase2-v1",
    )
    db.add_all([first_plan, second_plan])
    db.flush()
    activity = StudyActivity(
        plan_id=first_plan.id,
        scheduled_date=datetime.date(2026, 8, 16),
        minutes=20,
        activity_type="directed_reading",
        function_number=1,
        topic_id="topic-f1",
        topic_label="Facultades de fiscalización",
        source_document_id=source.id,
        source_locator="Artículo 684",
        objective="Distinguir las facultades aplicables al caso.",
        rationale="Es una función prioritaria y aún no medida.",
        status="planned",
    )
    db.add(activity)
    db.commit()

    assert first_plan.target_score == 85
    assert activity.source_document_id == source.id
    assert activity.source_locator == "Artículo 684"

    db.add(OpecStudyPlan(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=first.id,
        opec_number=first.opec_number,
        policy_version="duplicate",
    ))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    "changes",
    [
        {"target_score": 101},
        {"weekday_minutes": -1},
        {"saturday_minutes": 1441},
    ],
)
def test_study_plan_rejects_invalid_target_and_minutes(changes):
    _, db = _database()
    user, competition, first, _, _, _, _, _ = _seed(db)
    plan = OpecStudyPlan(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=first.id,
        opec_number=first.opec_number,
        weekday_minutes=30,
        saturday_minutes=60,
        study_days=[0, 1, 2, 3, 4, 5],
        policy_version="phase2-v1",
    )
    for field, value in changes.items():
        setattr(plan, field, value)
    db.add(plan)
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(
    "changes",
    [
        {"minutes": 0},
        {"activity_type": "watch_video"},
        {"status": "completed", "completed_at": None},
    ],
)
def test_study_activity_rejects_invalid_values(changes):
    _, db = _database()
    user, competition, first, _, _, _, _, source = _seed(db)
    plan = OpecStudyPlan(
        user_id=user.id,
        competition_id=competition.id,
        user_opec_id=first.id,
        opec_number=first.opec_number,
        policy_version="phase2-v1",
    )
    db.add(plan)
    db.flush()
    activity = StudyActivity(
        plan_id=plan.id,
        scheduled_date=datetime.date(2026, 8, 16),
        minutes=20,
        activity_type="directed_reading",
        source_document_id=source.id,
        source_locator="Artículo 684",
        objective="Distinguir las facultades aplicables.",
        rationale="Actividad prioritaria.",
        status="planned",
    )
    for field, value in changes.items():
        setattr(activity, field, value)
    db.add(activity)
    with pytest.raises(IntegrityError):
        db.commit()


def test_phase2_migration_is_dry_run_by_default_and_idempotent(tmp_path):
    engine = _engine(f"sqlite:///{tmp_path / 'phase2.db'}")
    legacy_tables = (
        User.__table__,
        Competition.__table__,
        UserOPEC.__table__,
        CaseStudy.__table__,
        Question.__table__,
        QuestionRevision.__table__,
        SourceDocument.__table__,
    )
    Base.metadata.create_all(engine, tables=legacy_tables)
    inspector = inspect(engine)
    legacy_columns = {
        table.name: tuple(column["name"] for column in inspector.get_columns(table.name))
        for table in legacy_tables
    }

    dry_run = migrate(engine)
    assert dry_run.applied is False
    assert dry_run.safe_to_apply is True
    assert set(dry_run.tables_to_create) == {table.name for table in PHASE2_TABLES}
    assert not ({table.name for table in PHASE2_TABLES} & set(inspect(engine).get_table_names()))

    first = migrate(engine, apply=True)
    assert first.applied is True
    assert set(first.tables_created) == {table.name for table in PHASE2_TABLES}
    second = migrate(engine, apply=True)
    assert second.applied is True
    assert second.tables_created == ()
    assert second.tables_to_create == ()

    after = inspect(engine)
    for table in legacy_tables:
        assert tuple(column["name"] for column in after.get_columns(table.name)) == legacy_columns[table.name]


def test_phase2_apply_refuses_database_without_dependencies():
    engine = _engine()
    with pytest.raises(PreflightError):
        migrate(engine, apply=True)
    assert not set(inspect(engine).get_table_names())
