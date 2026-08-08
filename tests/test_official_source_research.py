from types import SimpleNamespace

from core.official_source_research import (
    build_official_source_matrix,
    source_titles_for_function,
)


def _opec(functions):
    return SimpleNamespace(
        job_title="Profesional especializado", purpose="Gestionar arquitectura TI",
        functions=functions, requirements="Ingeniería de sistemas",
    )


def test_every_opec_gets_core_official_sources_and_guide_monitoring():
    rows = build_official_source_matrix(_opec(["Coordinar equipos"]), SimpleNamespace(code="NUEVO"))
    assert all(row["url"].startswith("https://") for row in rows)
    assert any("SIMO" in row["title"] for row in rows)
    assert any(row["status"] == "monitorear_guia" for row in rows)
    assert all("google" not in row["url"] for row in rows)


def test_ti_opec_gets_mintic_sources_without_claiming_a_specific_guide():
    rows = build_official_source_matrix(
        _opec(["Gestionar seguridad, PETI y arquitectura de sistemas"]),
        SimpleNamespace(code="ALIMENTACION-ESCOLAR-ABIERTO"),
    )
    titles = " ".join(row["title"] for row in rows)
    assert "MinTIC" in titles
    assert "Alimentos para Aprender" in titles
    assert any(row["status"] == "monitorear_guia" for row in rows)


def test_function_references_are_selected_by_domain():
    refs = source_titles_for_function("Supervisar un contrato con proveedor de software")
    assert any("Colombia Compra" in title for title in refs)
    assert any("Arquitectura Empresarial" in title for title in refs)
