import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from core.learning.engine import editorial_question_difficulty
from core.learning.session_service import LearningSessionService
from core.question_revision import question_revision_hash
from db.models import (
    Base,
    Competition,
    OpecProfile,
    Question,
    QuestionCitation,
    QuestionOpecScope,
    QuestionRevision,
    SourceDocument,
    User,
    UserOPEC,
)
from services.question_service import QuestionService


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _question(competition_id, opec_number):
    return Question(
        competition_id=competition_id,
        track="FUNCIONAL",
        competency="Fiscalización",
        topic=f"OPEC {opec_number} F01 · Tema",
        micro_competencia=f"OPEC {opec_number} F01 · Tema",
        difficulty=2,
        question_type="SITUATIONAL",
        stem=f"Situación exclusiva de la OPEC {opec_number}.",
        options_json={"A": "Uno", "B": "Dos", "C": "Tres"},
        correct_key="A",
        rationale="La fuente citada sustenta de forma directa la decisión descrita.",
        source_refs=f"OPEC {opec_number} · fuente provisional",
        hash_norm=f"hash-{opec_number}",
        is_verified=True,
        quality_report={
            "review": "human_source_grounded",
            "source_verification": {
                "status": "official_current",
                "url": "https://normograma.dian.gov.co/dian/compilacion/docs/estatuto_tributario.htm",
                "locator": "Artículo 684",
                "supporting_excerpt": "La Administración Tributaria tiene amplias facultades de fiscalización.",
                "verified_on": "2026-08-15",
                "verified_by": "prueba editorial",
            },
        },
    )


def _add_delivery_evidence(
    db,
    question,
    *,
    partition="training",
    revision_number=1,
    revision_status="approved",
    content_hash=None,
    source_status="current",
    official_url=(
        "https://normograma.dian.gov.co/dian/compilacion/"
        "docs/estatuto_tributario.htm"
    ),
    excerpt="La administración dispone de facultades de fiscalización.",
    add_citation=True,
):
    db.flush()
    revision = QuestionRevision(
        question_id=question.question_id,
        revision_number=revision_number,
        content_hash=(
            content_hash
            or question_revision_hash(
                question, editorial_question_difficulty(question)
            )
        ),
        stem=question.stem,
        options_json=dict(question.options_json),
        correct_key=question.correct_key,
        rationale=question.rationale,
        difficulty_level=editorial_question_difficulty(question),
        bank_partition=partition,
        source_snapshot=dict(question.quality_report["source_verification"]),
        status=revision_status,
        actor="test-editor",
        actor_type="human",
    )
    db.add(revision)
    if not add_citation:
        return revision
    document = SourceDocument(
        document_key=f"doc-{question.question_id}-{revision_number}",
        title="Estatuto Tributario",
        entity="DIAN",
        document_type="norma",
        official_url=official_url,
        validity_status=source_status,
        last_verified_at=datetime.datetime(2026, 8, 15),
    )
    db.add(document)
    db.flush()
    db.add(
        QuestionCitation(
            question_id=question.question_id,
            source_document_id=document.id,
            locator="Artículo 684",
            excerpt=excerpt,
            supports_key=True,
            verified_at=datetime.datetime(2026, 8, 15),
            verified_by="test-editor",
        )
    )
    return revision


def test_question_service_excludes_other_opec_in_same_competition():
    db = _db()
    user = User(username="ana", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-TEST", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    db.add_all([
        active_opec,
        _question(competition.id, "236769"),
        _question(competition.id, "242699"),
    ])
    db.commit()

    questions = QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    )

    assert [question.topic for question in questions] == ["OPEC 236769 F01 · Tema"]


def test_unscoped_question_is_quarantined_from_an_opec_bank():
    db = _db()
    user = User(username="bea", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-TEST-2", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    generic = _question(competition.id, "236769")
    generic.topic = "Fiscalización general"
    generic.micro_competencia = ""
    generic.stem = "Situación sin alcance OPEC demostrable."
    generic.source_refs = "Estatuto Tributario"
    db.add_all([active_opec, generic])
    db.commit()

    questions = QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    )

    assert questions == []


def test_explicit_scope_is_authoritative_and_can_be_shared():
    db = _db()
    user = User(username="carla", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-TEST-3", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    first_profile = OpecProfile(
        competition_id=competition.id, opec_number="236769"
    )
    second_profile = OpecProfile(
        competition_id=competition.id, opec_number="242699"
    )
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    # Its text points at 242699 on purpose: persisted scope must win.
    shared = _question(competition.id, "242699")
    db.add_all([first_profile, second_profile, active_opec, shared])
    db.flush()
    db.add_all([
        QuestionOpecScope(
            question_id=shared.question_id,
            opec_profile_id=first_profile.id,
            function_number=1,
            scope_kind="shared",
        ),
        QuestionOpecScope(
            question_id=shared.question_id,
            opec_profile_id=second_profile.id,
            function_number=1,
            scope_kind="shared",
        ),
    ])
    _add_delivery_evidence(db, shared)
    db.commit()

    questions = QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    )

    assert [question.question_id for question in questions] == [shared.question_id]


def test_reserved_partition_is_never_exposed_by_practice_service():
    db = _db()
    user = User(username="dora", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-TEST-4", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    reserved = _question(competition.id, "236769")
    db.add_all([profile, active_opec, reserved])
    db.flush()
    db.add(QuestionOpecScope(
        question_id=reserved.question_id,
        opec_profile_id=profile.id,
        function_number=1,
        bank_partition="reserved",
    ))
    db.commit()

    assert QuestionService.get_questions_for_user(
        db, user.id, competition_id=competition.id, user_opec=active_opec
    ) == []


def test_bank_partitions_are_isolated_by_use_case():
    db = _db()
    user = User(username="elena", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-TEST-5", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    training = _question(competition.id, "236769")
    training.hash_norm = "partition-training"
    measurement = _question(competition.id, "236769")
    measurement.hash_norm = "partition-measurement"
    anchor = _question(competition.id, "236769")
    anchor.hash_norm = "partition-anchor"
    db.add_all([profile, active_opec, training, measurement, anchor])
    db.flush()
    db.add_all([
        QuestionOpecScope(
            question_id=training.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        ),
        QuestionOpecScope(
            question_id=measurement.question_id,
            opec_profile_id=profile.id,
            bank_partition="measurement",
        ),
        QuestionOpecScope(
            question_id=anchor.question_id,
            opec_profile_id=profile.id,
            bank_partition="anchor",
        ),
    ])
    _add_delivery_evidence(db, training, partition="training")
    _add_delivery_evidence(db, measurement, partition="measurement")
    _add_delivery_evidence(db, anchor, partition="anchor")
    db.commit()

    practice = QuestionService.get_questions_for_user(
        db, user.id, competition_id=competition.id, user_opec=active_opec
    )
    exam = QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
        bank_partitions=("measurement",),
    )

    assert [item.question_id for item in practice] == [training.question_id]
    assert [item.question_id for item in exam] == [measurement.question_id]


def test_canonical_scope_without_revision_and_citation_is_not_delivered():
    db = _db()
    user = User(username="gate-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-GATE", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    candidate = _question(competition.id, "236769")
    db.add_all([profile, active_opec, candidate])
    db.flush()
    db.add(
        QuestionOpecScope(
            question_id=candidate.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        )
    )
    db.commit()

    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    ) == []
    assert [item.question_id for item in QuestionService.get_questions_for_user(
        db,
        user.id,
        include_review=True,
        competition_id=competition.id,
        user_opec=active_opec,
    )] == [candidate.question_id]


def test_newer_nonapproved_revision_closes_canonical_delivery():
    db = _db()
    user = User(username="revision-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-REVISION", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    question = _question(competition.id, "236769")
    db.add_all([profile, active_opec, question])
    db.flush()
    db.add(
        QuestionOpecScope(
            question_id=question.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        )
    )
    _add_delivery_evidence(db, question, revision_number=1)
    _add_delivery_evidence(
        db,
        question,
        revision_number=2,
        revision_status="candidate",
        add_citation=False,
    )
    db.commit()

    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    ) == []


def test_canonical_gate_rejects_stale_content_or_noncurrent_source():
    db = _db()
    user = User(username="source-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-SOURCE", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    stale_revision = _question(competition.id, "236769")
    stale_revision.hash_norm = "stale-revision"
    pending_source = _question(competition.id, "236769")
    pending_source.hash_norm = "pending-source"
    db.add_all([profile, active_opec, stale_revision, pending_source])
    db.flush()
    db.add_all([
        QuestionOpecScope(
            question_id=stale_revision.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        ),
        QuestionOpecScope(
            question_id=pending_source.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        ),
    ])
    _add_delivery_evidence(
        db,
        stale_revision,
        content_hash="0" * 64,
    )
    _add_delivery_evidence(
        db,
        pending_source,
        source_status="pending",
    )
    db.commit()

    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    ) == []


def test_canonical_gate_rejects_short_citation_excerpt():
    db = _db()
    user = User(username="excerpt-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-EXCERPT", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    question = _question(competition.id, "236769")
    db.add_all([profile, active_opec, question])
    db.flush()
    db.add(
        QuestionOpecScope(
            question_id=question.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        )
    )
    _add_delivery_evidence(db, question, excerpt="Muy corto")
    db.commit()

    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    ) == []


def test_latest_revision_must_match_the_questions_exact_scope_partition():
    db = _db()
    user = User(username="partition-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-PARTITION-GATE", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    question = _question(competition.id, "236769")
    db.add_all([profile, active_opec, question])
    db.flush()
    db.add(
        QuestionOpecScope(
            question_id=question.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        )
    )
    _add_delivery_evidence(db, question, partition="measurement")
    db.commit()

    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
        bank_partitions=("training", "measurement"),
    ) == []


def test_canonical_evidence_is_loaded_in_batches_not_per_question():
    db = _db()
    user = User(username="batch-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-BATCH", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    db.add_all([profile, active_opec])
    for index in range(6):
        question = _question(competition.id, "236769")
        question.hash_norm = f"batch-{index}"
        db.add(question)
        db.flush()
        db.add(
            QuestionOpecScope(
                question_id=question.question_id,
                opec_profile_id=profile.id,
                bank_partition="training",
            )
        )
        _add_delivery_evidence(db, question)
    db.commit()

    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        delivered = QuestionService.get_questions_for_user(
            db,
            user.id,
            competition_id=competition.id,
            user_opec=active_opec,
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    assert len(delivered) == 6
    assert select_count <= 8


def test_non_training_partition_fails_closed_without_phase1_schema():
    db = _db()
    user = User(username="fabio", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-TEST-6", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    legacy = _question(competition.id, "236769")
    db.add_all([active_opec, legacy])
    db.commit()

    # A canonical profile is intentionally absent. Measurement may never fall
    # back to legacy text inference.
    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
        bank_partitions=("measurement",),
    ) == []


def test_canonical_evidence_is_authoritative_for_service_and_tutor():
    db = _db()
    user = User(username="canonical-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-CANONICAL", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    deliverable = _question(competition.id, "236769")
    deliverable.hash_norm = "canonical-deliverable"
    stale = _question(competition.id, "236769")
    stale.hash_norm = "canonical-stale"
    db.add_all([profile, active_opec, deliverable, stale])
    db.flush()
    db.add_all([
        QuestionOpecScope(
            question_id=deliverable.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        ),
        QuestionOpecScope(
            question_id=stale.question_id,
            opec_profile_id=profile.id,
            bank_partition="training",
        ),
    ])
    _add_delivery_evidence(db, deliverable)
    _add_delivery_evidence(db, stale, content_hash="0" * 64)

    # The legacy report is deliberately insufficient. Canonical revision and
    # citation evidence must be authoritative for explicitly scoped banks.
    deliverable.quality_report = {"review": "human_source_grounded"}
    stale.quality_report = {"review": "human_source_grounded"}
    db.commit()

    delivered = QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    )
    tutor_questions = LearningSessionService(db)._questions(
        competition.id,
        user.id,
        user_opec=active_opec,
    )

    assert [item.question_id for item in delivered] == [deliverable.question_id]
    assert [item.question_id for item in tutor_questions] == [deliverable.question_id]


def test_canonical_failure_is_not_recovered_by_tutor_scope_fallback():
    db = _db()
    user = User(username="closed-gate-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-CLOSED-GATE", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    profile = OpecProfile(competition_id=competition.id, opec_number="236769")
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    stale = _question(competition.id, "236769")
    db.add_all([profile, active_opec, stale])
    db.flush()
    db.add(QuestionOpecScope(
        question_id=stale.question_id,
        opec_profile_id=profile.id,
        bank_partition="training",
    ))
    _add_delivery_evidence(db, stale, content_hash="0" * 64)
    db.commit()

    assert LearningSessionService(db)._questions(
        competition.id,
        user.id,
        user_opec=active_opec,
    ) == []


def test_legacy_scope_still_requires_the_legacy_quality_gate():
    db = _db()
    user = User(username="legacy-gate-user", password_hash="x", subscription_tier="free")
    competition = Competition(code="DIAN-LEGACY-GATE", name="DIAN")
    db.add_all([user, competition])
    db.flush()
    active_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=["Función"],
        is_active=True,
    )
    unsafe = _question(competition.id, "236769")
    unsafe.quality_report = {"review": "human_source_grounded"}
    db.add_all([active_opec, unsafe])
    db.commit()

    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=active_opec,
    ) == []
