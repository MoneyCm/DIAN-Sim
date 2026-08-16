import ast
from pathlib import Path


PAGE = Path("app/pages/8_Panel_Admin.py")


def _source() -> str:
    return PAGE.read_text(encoding="utf-8")


def _literal_assignment(name: str):
    tree = ast.parse(_source())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"Missing assignment: {name}")


def test_policy_tab_is_admin_only_and_uses_versioned_store():
    source = _source()
    assert source.index("require_admin()") < source.index("Política de simulacros")
    assert "simulation_policy_schema_available(" in source
    assert "load_active_simulation_policy(" in source
    assert "create_initial_simulation_policy(" in source
    assert "create_simulation_policy_version(" in source
    assert "Crear y activar nueva versión" in source
    assert "active_policy.internal_" not in source


def test_opec_236769_seed_contains_only_supported_partial_exam_fact():
    partial = _literal_assignment("OPEC_236769_OFFICIAL_PARTIAL")
    assert partial["official_max_questions_per_case"] == 3
    assert partial["official_source_status"] == "partial"
    assert partial["official_source_version"] == "LP-004-2026"
    assert partial["official_source_url"].startswith("https://community.secop.gov.co/")
    assert "official_question_count" not in partial
    assert "official_duration_minutes" not in partial
    assert "official_minutes_per_question" not in partial
    assert "official_navigation_mode" not in partial


def test_internal_and_official_fields_are_visibly_separate_and_nullable():
    source = _source()
    policy_section = source.split("# --- TAB: OPEC SIMULATION POLICY ---", 1)[1].split(
        "# --- TAB: NORMATIVA ---", 1
    )[0]
    assert "Configuración interna" in policy_section
    assert "Campos oficiales opcionales" in policy_section
    assert "Vacío = NULL" in policy_section
    assert "nunca se completa con el valor interno" in policy_section
    assert '"official_question_count": _optional_admin_int(' in policy_section
    assert '"official_duration_minutes": _optional_admin_int(' in policy_section
    assert "official.question_count" in policy_section
    assert "resolved_policy.internal" not in policy_section.split(
        "Campos oficiales opcionales", 1
    )[1].split("create_version", 1)[0]


def test_new_version_requires_reason_and_unexpected_errors_are_redacted():
    source = _source()
    policy_section = source.split("# --- TAB: OPEC SIMULATION POLICY ---", 1)[1].split(
        "# --- TAB: NORMATIVA ---", 1
    )[0]
    assert "if not change_reason.strip():" in policy_section
    assert "Explica el motivo del cambio de política." in policy_section
    assert "La fuente oficial debe usar una URL HTTPS." in policy_section
    assert "No fue posible crear la nueva versión." in policy_section
    assert "No fue posible cargar las políticas de simulacro." in policy_section
    assert "st.error(f" not in policy_section
