from core.opec_source_catalog import FICHA_236769, sources_for_opec_function


def test_known_opec_function_has_catalogue_sources():
    sources = sources_for_opec_function(
        "236769", "Acciones de fiscalización tributaria y aduanera"
    )
    assert FICHA_236769 in sources
    assert any("Estatuto Tributario" in item for item in sources)
    assert any("régimen de aduanas" in item for item in sources)


def test_unknown_opec_does_not_receive_dian_catalogue():
    assert sources_for_opec_function("999999", "Fiscalización") == []
