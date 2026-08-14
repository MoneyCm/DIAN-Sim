from types import SimpleNamespace

from core.source_evidence import assess_source_evidence, record_source_evidence


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


def test_untraceable_source_is_not_promoted_by_an_ai_score():
    item = question(source_refs="Inyección Especial Antigravity", stem="Situación laboral")

    evidence = record_source_evidence(item)

    assert evidence["status"] == "UNTRACEABLE"
    assert item.quality_report["source_evidence"]["status"] == "UNTRACEABLE"
