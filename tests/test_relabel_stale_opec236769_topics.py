import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.learning.engine import topic_id_for
from db.models import (
    Base,
    CaseStudy,
    OpecLearningEvent,
    OpecProfile,
    OpecTopicState,
    Question,
    QuestionOpecScope,
    TopicMastery,
)
from scripts.migrations.relabel_stale_opec236769_topics import repair


OLD_TOPIC = "F3 - Gestión documental, peticiones e informes"
NEW_TOPIC = "F9 - Gestión documental, peticiones e informes"
CASE_KEY = "goa-236769-f3-documentos-pqrs-informes-01"


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _fixture(db):
    case_id = str(uuid.uuid5(uuid.NAMESPACE_URL, CASE_KEY))
    case = CaseStudy(
        id=case_id,
        competition_id=1,
        title="Organización documental",
        text="Un expediente requiere gestión documental y atención de una denuncia.",
        difficulty=3,
        topic=OLD_TOPIC,
    )
    question = Question(
        question_id="phase16-question",
        competition_id=1,
        case_id=case_id,
        track="FUNCIONAL",
        competency=OLD_TOPIC,
        topic=OLD_TOPIC,
        micro_competencia="OPEC 236769 F9 · " + OLD_TOPIC,
        difficulty=3,
        stem="¿Cómo debe proceder con la denuncia asignada?",
        options_json={"A": "Atenderla", "B": "Ignorarla", "C": "Ocultarla"},
        correct_key="A",
        rationale="Debe atenderla según el procedimiento.",
        hash_norm="phase16-question-hash",
    )
    profile = OpecProfile(
        id=1,
        competition_id=1,
        opec_number="236769",
        job_title="Gestor III",
        source_status="official_verified",
    )
    db.add_all([case, question, profile])
    db.flush()
    db.add(QuestionOpecScope(
        question_id=question.question_id,
        opec_profile_id=profile.id,
        function_number=9,
        bank_partition="training",
    ))
    old_id = topic_id_for("FUNCIONAL", OLD_TOPIC, OLD_TOPIC)
    db.add_all([
        TopicMastery(
            user_id=1,
            competition_id=1,
            topic_id=old_id,
            topic_label=OLD_TOPIC,
            competency=OLD_TOPIC,
            track="FUNCIONAL",
            mastery_score=20,
            attempts=1,
            correct_attempts=1,
        ),
        OpecTopicState(
            user_id=1,
            competition_id=1,
            user_opec_id=1,
            opec_number="236769",
            topic_id=old_id,
            topic_label=OLD_TOPIC,
            function_number=9,
            mastery_score=20,
            evidence_count=1,
        ),
    ])
    db.commit()
    return case_id, question.question_id


def test_repair_relabels_question_and_preserves_mastery_idempotently():
    db = _db()
    case_id, question_id = _fixture(db)

    preview = repair(db, apply=False)
    assert preview["questions"] == 1
    assert db.get(Question, question_id).topic == OLD_TOPIC

    applied = repair(db, apply=True)
    new_id = topic_id_for("FUNCIONAL", NEW_TOPIC, NEW_TOPIC)

    assert applied["questions"] == 1
    assert db.get(CaseStudy, case_id).topic == NEW_TOPIC
    assert db.get(Question, question_id).topic == NEW_TOPIC
    assert db.query(TopicMastery).filter_by(topic_id=new_id).one().mastery_score == 20
    assert db.query(OpecTopicState).filter_by(topic_id=new_id).one().mastery_score == 20
    assert repair(db, apply=True) == {
        "cases": 0,
        "questions": 0,
        "events": 0,
        "legacy_mastery": 0,
        "opec_states": 0,
        "skills": 0,
    }
