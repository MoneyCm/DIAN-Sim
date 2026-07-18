import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.anki_enrichment import enrich_question, needs_enrichment, question_source_hash
from db.models import Base, Question, QuestionAnkiEnrichment


def make_question():
    return Question(
        track="FUNCIONAL",
        competency="Procedimiento tributario",
        topic="Fiscalización",
        difficulty=2,
        stem="¿Cuál actuación debe realizar el funcionario?",
        options_json={"A": "Archivar", "B": "Notificar el acto", "C": "Omitir el trámite"},
        correct_key="B",
        rationale="Debe notificarse el acto antes de continuar.",
        source_refs="Estatuto Tributario",
        hash_norm="anki-enrichment-test",
    )


def test_enrichment_is_generated_and_cached():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    question = make_question()
    db.add(question)
    db.commit()

    calls = []

    def fake_generator(prompt):
        calls.append(prompt)
        return {
            "rule": "Notificar el acto antes de continuar.",
            "exception": "No identificada en la fuente.",
            "distractor": "Archivar parece eficiente, pero omite la notificación obligatoria.",
        }

    enrichment = enrich_question(db, question, "gemini", "", generator=fake_generator)
    assert enrichment.status == "generated"
    assert enrichment.source_hash == question_source_hash(question)
    assert db.query(QuestionAnkiEnrichment).count() == 1
    assert not needs_enrichment(question)

    cached = enrich_question(db, question, "gemini", "", generator=fake_generator)
    assert cached.id == enrichment.id
    assert len(calls) == 1
    db.close()


def test_changed_question_requires_regeneration():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    question = make_question()
    db.add(question)
    db.commit()

    payload = {
        "rule": "Regla",
        "exception": "Excepción",
        "distractor": "Distractor",
    }
    enrich_question(db, question, "gemini", "", generator=lambda prompt: payload)
    question.rationale = "La justificación cambió."
    assert needs_enrichment(question)
    db.close()