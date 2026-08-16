import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.bank_partition import (
    ASPIRANT_VISIBLE_PARTITIONS,
    MAX_PARTITION_BATCH,
    BankPartitionContextError,
    BankPartitionEligibilityError,
    BankPartitionError,
    has_precise_canonical_citation,
    list_partition_items,
    move_question_partitions,
    partition_counts,
    partition_eligibility,
    resolve_active_bank_context,
)
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


NOW = datetime.datetime(2026, 8, 15, 12, 0)


def _database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _safe_report():
    return {
        "review": "source_grounded",
        "source_verification": {
            "status": "official_current",
            "url": "https://www.dian.gov.co/normativa/documento",
            "locator": "Artículo 684",
            "supporting_excerpt": "La administración puede ejercer amplias facultades de fiscalización.",
            "verified_on": "2026-08-15",
            "verified_by": "equipo-editorial",
        },
    }


def _seed(*, partition="training"):
    db = _database()
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash="hash",
        role="admin",
    )
    competition = Competition(code="DIAN-2676", name="DIAN 2676")
    db.add_all([user, competition])
    db.flush()
    user_opec = UserOPEC(
        user_id=user.id,
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        functions=[],
        is_active=True,
        updated_at=NOW,
    )
    profile = OpecProfile(
        competition_id=competition.id,
        opec_number="236769",
        job_title="Gestor III",
        source_status="verified",
    )
    question = Question(
        question_id="question-partition-1",
        competition_id=competition.id,
        track="FUNCIONAL",
        competency="Fiscalización",
        topic="OPEC 236769 · Fiscalización",
        difficulty=2,
        question_type="SITUATIONAL",
        stem="Ante una inconsistencia tributaria, ¿qué actuación procede primero?",
        options_json={"A": "Verificar hechos", "B": "Sancionar", "C": "Archivar"},
        correct_key="A",
        rationale="Primero se contrastan los hechos con la regla aplicable.",
        source_refs="Estatuto Tributario, artículo 684",
        hash_norm="partition-question-hash",
        is_verified=True,
        quality_report=_safe_report(),
    )
    db.add_all([user_opec, profile, question])
    db.flush()
    scope = QuestionOpecScope(
        question_id=question.question_id,
        opec_profile_id=profile.id,
        function_number=1,
        scope_kind="primary",
        bank_partition=partition,
    )
    revision = QuestionRevision(
        id="revision-partition-1",
        question_id=question.question_id,
        revision_number=1,
        content_hash="a" * 64,
        stem=question.stem,
        options_json=question.options_json,
        correct_key=question.correct_key,
        rationale=question.rationale,
        difficulty_level=5,
        bank_partition=partition,
        source_snapshot=_safe_report()["source_verification"],
        status="approved",
        actor="editor",
        actor_type="human",
    )
    source = SourceDocument(
        document_key="et-current",
        title="Estatuto Tributario",
        entity="DIAN",
        document_type="estatuto",
        official_url="https://www.dian.gov.co/normativa/estatuto",
        validity_status="current",
        last_verified_at=NOW,
    )
    db.add_all([scope, revision, source])
    db.flush()
    citation = QuestionCitation(
        question_id=question.question_id,
        source_document_id=source.id,
        locator="Artículo 684",
        excerpt="La administración tributaria dispone de facultades de fiscalización.",
        supports_key=True,
        verified_at=NOW,
        verified_by="equipo-editorial",
    )
    db.add(citation)
    db.commit()
    return db, user, competition, user_opec, profile, question, scope, revision, citation


def _context(db, user, competition):
    return resolve_active_bank_context(
        db,
        user_id=user.id,
        competition_id=competition.id,
    )


def test_move_is_atomic_revision_backed_and_keeps_one_opec_scope():
    db, user, competition, _, profile, question, scope, revision, _ = _seed()
    context = _context(db, user, competition)
    assert context.opec_profile_id == profile.id
    assert has_precise_canonical_citation(db, question_id=question.question_id)

    moves = move_question_partitions(
        db,
        context=context,
        question_ids=[question.question_id],
        from_partition="training",
        to_partition="measurement",
        actor="admin@example.com",
        reason="Incorporación al banco de medición controlada.",
    )
    db.commit()

    assert len(moves) == 1
    assert scope.bank_partition == "measurement"
    revisions = (
        db.query(QuestionRevision)
        .filter_by(question_id=question.question_id)
        .order_by(QuestionRevision.revision_number)
        .all()
    )
    assert [item.revision_number for item in revisions] == [1, 2]
    assert revisions[-1].status == "approved"
    assert revisions[-1].bank_partition == "measurement"
    assert revisions[-1].actor == "admin@example.com"
    assert revisions[-1].actor_type == "admin_partition_move"
    assert "training → measurement" in revisions[-1].change_reason
    assert db.query(QuestionOpecScope).filter_by(
        question_id=question.question_id,
        opec_profile_id=profile.id,
    ).count() == 1
    assert partition_counts(db, opec_profile_id=profile.id) == {
        "training": 0,
        "measurement": 1,
        "anchor": 0,
        "reserved": 0,
    }


@pytest.mark.parametrize("broken_gate", ["study", "revision", "citation"])
def test_question_cannot_leave_training_without_every_editorial_gate(broken_gate):
    db, user, competition, _, _, question, scope, revision, citation = _seed()
    context = _context(db, user, competition)
    if broken_gate == "study":
        question.is_verified = False
    elif broken_gate == "revision":
        revision.status = "candidate"
    else:
        citation.verified_at = None
    db.commit()

    result = partition_eligibility(
        db,
        question=question,
        current_partition="training",
    )
    assert result.eligible is False
    with pytest.raises(BankPartitionEligibilityError):
        move_question_partitions(
            db,
            context=context,
            question_ids=[question.question_id],
            from_partition="training",
            to_partition="anchor",
            actor="admin",
            reason="Promoción editorial controlada.",
        )
    db.rollback()
    assert scope.bank_partition == "training"
    assert db.query(QuestionRevision).filter_by(question_id=question.question_id).count() == 1


def test_mixed_batch_is_preflighted_before_any_scope_is_changed():
    db, user, competition, _, profile, first, first_scope, _, citation = _seed()
    second = Question(
        question_id="question-partition-2",
        competition_id=competition.id,
        track="FUNCIONAL",
        competency="Fiscalización",
        topic="OPEC 236769 · Pruebas",
        difficulty=2,
        question_type="SITUATIONAL",
        stem="¿Qué prueba debe valorarse dentro del expediente?",
        options_json={"A": "La pertinente", "B": "Ninguna", "C": "Solo rumores"},
        correct_key="A",
        rationale="La prueba pertinente debe incorporarse y valorarse.",
        source_refs="Estatuto Tributario, artículo 742",
        hash_norm="partition-question-hash-2",
        is_verified=True,
        quality_report=_safe_report(),
    )
    db.add(second)
    db.flush()
    second_scope = QuestionOpecScope(
        question_id=second.question_id,
        opec_profile_id=profile.id,
        bank_partition="training",
    )
    second_revision = QuestionRevision(
        question_id=second.question_id,
        revision_number=1,
        content_hash="b" * 64,
        stem=second.stem,
        options_json=second.options_json,
        correct_key="A",
        rationale=second.rationale,
        bank_partition="training",
        status="candidate",
    )
    second_citation = QuestionCitation(
        question_id=second.question_id,
        source_document_id=citation.source_document_id,
        locator="Artículo 742",
        excerpt="Las decisiones deben fundarse en los hechos probados dentro del expediente.",
        supports_key=True,
        verified_at=NOW,
        verified_by="equipo-editorial",
    )
    db.add_all([second_scope, second_revision, second_citation])
    db.commit()

    with pytest.raises(BankPartitionEligibilityError):
        move_question_partitions(
            db,
            context=_context(db, user, competition),
            question_ids=[first.question_id, second.question_id],
            from_partition="training",
            to_partition="measurement",
            actor="admin",
            reason="Validación atómica del lote editorial.",
        )
    db.rollback()

    assert first_scope.bank_partition == "training"
    assert second_scope.bank_partition == "training"
    assert db.query(QuestionRevision).filter_by(question_id=first.question_id).count() == 1


def test_reserved_inventory_is_opaque_and_training_is_the_only_aspirant_partition(
    monkeypatch,
):
    db, user, competition, user_opec, profile, question, _, _, _ = _seed(
        partition="reserved"
    )
    original_get = db.get

    def reject_reserved_content_lookup(entity, identifier):
        if entity is Question:
            raise AssertionError("Reserved inventory must not load question content.")
        return original_get(entity, identifier)

    monkeypatch.setattr(db, "get", reject_reserved_content_lookup)
    items = list_partition_items(
        db,
        opec_profile_id=profile.id,
        partition="reserved",
    )
    monkeypatch.setattr(db, "get", original_get)

    assert ASPIRANT_VISIBLE_PARTITIONS == {"training"}
    assert len(items) == 1
    item = items[0]
    assert item.display_label == "Elemento reservado 1"
    assert question.topic not in item.display_label
    assert question.question_id not in item.display_label
    assert not hasattr(item, "stem")
    assert not hasattr(item, "correct_key")
    assert not hasattr(item, "options_json")
    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=user_opec,
        bank_partitions=("reserved",),
    ) == []


def test_shared_opec_scope_is_rejected_instead_of_becoming_inconsistent():
    db, user, competition, _, _, question, scope, _, _ = _seed()
    context = _context(db, user, competition)
    other_profile = OpecProfile(
        competition_id=competition.id,
        opec_number="242699",
        job_title="Analista I",
    )
    db.add(other_profile)
    db.flush()
    db.add(
        QuestionOpecScope(
            question_id=question.question_id,
            opec_profile_id=other_profile.id,
            scope_kind="shared",
            bank_partition="training",
        )
    )
    db.commit()

    with pytest.raises(BankPartitionContextError, match="compartidos"):
        move_question_partitions(
            db,
            context=context,
            question_ids=[question.question_id],
            from_partition="training",
            to_partition="measurement",
            actor="admin",
            reason="Movimiento coordinado pendiente.",
        )
    db.rollback()
    assert scope.bank_partition == "training"


def test_question_delivery_fails_closed_without_an_active_opec():
    db, user, competition, user_opec, _, _, _, _, _ = _seed()
    user_opec.is_active = False
    db.commit()

    assert QuestionService.get_questions_for_user(
        db,
        user.id,
        competition_id=competition.id,
        user_opec=None,
        bank_partitions=("training",),
    ) == []


def test_partition_move_rejects_a_stale_active_opec_context():
    db, user, competition, _, _, question, scope, _, _ = _seed()
    context = _context(db, user, competition)
    db.add(
        UserOPEC(
            user_id=user.id,
            competition_id=competition.id,
            opec_number="242699",
            job_title="Analista I",
            functions=[],
            is_active=True,
            updated_at=NOW + datetime.timedelta(minutes=1),
        )
    )
    db.commit()

    with pytest.raises(BankPartitionContextError, match="OPEC activa cambió"):
        move_question_partitions(
            db,
            context=context,
            question_ids=[question.question_id],
            from_partition="training",
            to_partition="measurement",
            actor="admin",
            reason="Movimiento basado en un contexto obsoleto.",
        )
    db.rollback()
    assert scope.bank_partition == "training"


def test_core_partition_move_rejects_a_non_admin_even_without_the_ui():
    db, user, competition, _, _, question, scope, _, _ = _seed()
    context = _context(db, user, competition)
    user.role = "user"
    db.commit()

    with pytest.raises(BankPartitionContextError, match="administrador autenticado"):
        move_question_partitions(
            db,
            context=context,
            question_ids=[question.question_id],
            from_partition="training",
            to_partition="anchor",
            actor=user.username,
            reason="Intento sin autorización administrativa.",
        )
    db.rollback()
    assert scope.bank_partition == "training"


def test_audit_actor_must_match_the_authenticated_administrator():
    db, user, competition, _, _, question, scope, _, _ = _seed()
    with pytest.raises(BankPartitionContextError, match="identidad de auditoría"):
        move_question_partitions(
            db,
            context=_context(db, user, competition),
            question_ids=[question.question_id],
            from_partition="training",
            to_partition="measurement",
            actor="otro-admin",
            reason="Intento con una identidad de auditoría distinta.",
        )
    db.rollback()
    assert scope.bank_partition == "training"


def test_batch_must_be_small_unique_explicit_and_confirmed_by_reason():
    db, user, competition, _, _, question, _, _, _ = _seed()
    common = dict(
        db=db,
        context=_context(db, user, competition),
        from_partition="training",
        to_partition="measurement",
        actor="admin",
        reason="Movimiento editorial controlado.",
    )
    with pytest.raises(BankPartitionError, match="duplicadas"):
        move_question_partitions(
            question_ids=[question.question_id, question.question_id],
            **common,
        )
    with pytest.raises(BankPartitionError, match="máximo"):
        move_question_partitions(
            question_ids=[f"question-{index}" for index in range(MAX_PARTITION_BATCH + 1)],
            **common,
        )
    with pytest.raises(BankPartitionError, match="motivo editorial"):
        move_question_partitions(
            question_ids=[question.question_id],
            **{**common, "reason": "corto"},
        )
    with pytest.raises(BankPartitionContextError, match="origen cambió"):
        move_question_partitions(
            question_ids=[question.question_id],
            **{**common, "from_partition": "anchor"},
        )


def test_admin_page_has_confirmed_small_batch_view_and_no_reserved_content_fields():
    page = (
        Path(__file__).parents[1] / "app" / "pages" / "5_Banco_Preguntas.py"
    ).read_text(encoding="utf-8-sig")
    assert '"Particiones del banco"' in page
    assert "move_question_partitions(" in page
    assert "MAX_PARTITION_BATCH" in page
    assert "Confirmo el movimiento editorial" in page
    assert "Contenido y claves reservadas permanecen ocultos" in page
