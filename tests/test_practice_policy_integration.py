from pathlib import Path


PAGE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "pages" / "1_Nuevo_Simulacro.py"
)


def test_partial_and_full_modes_use_versioned_opec_policy():
    source = PAGE_PATH.read_text(encoding="utf-8-sig")

    assert "load_active_simulation_policy" in source
    assert 'internal.mode("partial").question_count' in source
    assert 'internal.mode("full").question_count' in source
    assert "MODE_PARTIAL: 15" not in source
    assert "MODE_FULL: 30" not in source


def test_invalid_persisted_policy_blocks_instead_of_silently_falling_back():
    source = PAGE_PATH.read_text(encoding="utf-8-sig")

    assert "except SimulationPolicyValidationError as exc" in source
    assert "requiere corrección administrativa" in source
    assert "st.stop()" in source
