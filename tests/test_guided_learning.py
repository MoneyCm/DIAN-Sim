from types import SimpleNamespace

from core.guided_learning import build_guided_learning_brief


def test_brief_uses_topic_and_sources_without_exposing_rationale():
    question = SimpleNamespace(
        topic="Práctica de pruebas", macro_dominio="Fiscalización",
        source_refs="Estatuto Tributario, artículo 744", rationale="RESPUESTA SECRETA",
    )
    brief = build_guided_learning_brief([question], 8)
    assert brief["topic"] == "Práctica de pruebas"
    assert brief["sources"] == ["Estatuto Tributario, artículo 744"]
    assert "RESPUESTA SECRETA" not in str(brief)

