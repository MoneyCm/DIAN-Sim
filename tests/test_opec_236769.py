from core.opec_236769 import CASE_FUNCTIONS, function_label


def test_each_curated_case_has_one_explicit_opec_function():
    assert len(CASE_FUNCTIONS) == 48
    assert set(CASE_FUNCTIONS.values()) == set(range(1, 10))
    assert function_label("goa-236769-f9-revision-expediente-decision-01", "Revisión") == (
        "OPEC 236769 F9 · Revisión"
    )
