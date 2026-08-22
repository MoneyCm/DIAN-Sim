from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.source_evidence import (
    SOURCE_EVIDENCE_VERSION,
    assess_source_evidence,
    canonical_source_verification,
    record_source_evidence,
)
from db.models import Base, CaseStudy, Competition, Question, QuestionCitation, SourceDocument


def test_source_evidence_registry_exposes_current_official_link_version():
    assert SOURCE_EVIDENCE_VERSION == "official-links-v3"


def question(**values):
    base = {
        "source_refs": "",
        "stem": "",
        "rationale": "",
        "quality_report": {},
    }
    base.update(values)
    return SimpleNamespace(**base)


def test_estatuto_article_is_matched_to_a_catalogued_official_source():
    item = question(
        source_refs="Estatuto Tributario Colombiano",
        stem="Según el artículo 616-1, ¿qué exige la factura electrónica?",
    )

    evidence = assess_source_evidence(item)

    assert evidence["status"] == "DIRECT_OFFICIAL_SOURCE"
    assert evidence["article"] == "616-1"
    assert evidence["official_url"].startswith("https://micrositios.dian.gov.co/")


def test_decree_and_cpaca_anchors_link_to_their_official_texts():
    decree = assess_source_evidence(question(source_refs="Decreto 1165 de 2019, artículo 172"))
    cpaca = assess_source_evidence(question(source_refs="Ley 1437 de 2011, artículo 3"))

    assert decree["status"] == "DIRECT_OFFICIAL_SOURCE"
    assert decree["official_url"].startswith("https://www.suin-juriscol.gov.co/")
    assert cpaca["status"] == "DIRECT_OFFICIAL_SOURCE"
    assert cpaca["official_url"].startswith("https://www.suin-juriscol.gov.co/")


def test_other_estatuto_articles_link_to_the_official_statute_text():
    evidence = assess_source_evidence(
        question(source_refs="Estatuto Tributario Colombiano", stem="Articulo 746")
    )

    assert evidence["status"] == "DIRECT_OFFICIAL_SOURCE"
    assert evidence["official_url"].startswith("https://suin-juriscol.gov.co/")


def test_known_tax_and_dian_structure_decrees_link_to_official_texts():
    decree_1625 = assess_source_evidence(question(source_refs="Decreto 1625 de 2016"))
    decree_1742 = assess_source_evidence(question(source_refs="Decreto 1742 de 2020"))

    assert decree_1625["status"] == "DIRECT_OFFICIAL_SOURCE"
    assert "suin-juriscol.gov.co" in decree_1625["official_url"]
    assert decree_1742["status"] == "DIRECT_OFFICIAL_SOURCE"
    assert "funcionpublica.gov.co" in decree_1742["official_url"]


def test_untraceable_source_is_not_promoted_by_an_ai_score():
    item = question(source_refs="Inyección Especial Antigravity", stem="Situación laboral")

    evidence = record_source_evidence(item)

    assert evidence["status"] == "UNTRACEABLE"
    assert item.quality_report["source_evidence"]["status"] == "UNTRACEABLE"


def test_canonical_verification_uses_current_official_citation():
    db = sessionmaker(bind=create_engine("sqlite:///:memory:"))()
    Base.metadata.create_all(db.bind)
    competition = Competition(code="SOURCE", name="Source")
    case = CaseStudy(
        id="source-case",
        competition_id=None,
        title="Caso",
        text="Hechos suficientes para decidir.",
        difficulty=2,
        topic="F9 - Funciones comunes",
    )
    question_row = Question(
        question_id="source-question",
        competition_id=None,
        case_id=case.id,
        track="FUNCIONAL",
        competency="F9 - Funciones comunes",
        topic="F9 - Funciones comunes",
        difficulty=2,
        stem="¿Qué corresponde?",
        options_json={"A": "Atender", "B": "Ignorar", "C": "Ocultar"},
        correct_key="A",
        rationale="Debe atenderse según el procedimiento.",
        source_refs="Resolución 000067 de 2024, artículo 6, numeral 6",
        hash_norm="source-question-hash",
    )
    document = SourceDocument(
        document_key="resolution-67",
        title="Resolución DIAN 000067 de 2024",
        official_url="https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_0067_2024.htm",
        validity_status="current",
    )
    db.add_all([competition, case, question_row, document])
    db.flush()
    db.add(QuestionCitation(
        question_id=question_row.question_id,
        source_document_id=document.id,
        locator="Artículo 6, numeral 6",
        excerpt="Atender las peticiones, quejas, reclamos y denuncias asignadas.",
        supports_key=True,
        verified_at=datetime(2026, 8, 21, 12, 0),
        verified_by="auditoría canónica",
    ))
    db.flush()

    verification = canonical_source_verification(db, question_row.question_id)

    assert verification["status"] == "official_current"
    assert verification["locator"] == "Artículo 6, numeral 6"
    assert verification["url"].startswith("https://normograma.dian.gov.co/")


def test_canonical_verification_rejects_nonofficial_or_unverified_citation():
    db = sessionmaker(bind=create_engine("sqlite:///:memory:"))()
    Base.metadata.create_all(db.bind)
    document = SourceDocument(
        document_key="untrusted",
        title="Documento no oficial",
        official_url="https://example.com/norma",
        validity_status="current",
    )
    db.add(document)
    db.flush()
    db.add(QuestionCitation(
        question_id="missing-question",
        source_document_id=document.id,
        locator="Artículo 1",
        excerpt="Un fragmento suficientemente largo para la prueba.",
        supports_key=True,
        verified_at=None,
        verified_by="",
    ))

    assert canonical_source_verification(db, "missing-question") == {}
