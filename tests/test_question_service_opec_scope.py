from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import (
    Base,
    Competition,
    OpecProfile,
    Question,
    QuestionOpecScope,
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
