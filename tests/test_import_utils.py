import pandas as pd

from core.import_utils import validate_import_df


def _frame(**updates):
    row = {
        "track": "FUNCIONAL",
        "competency": "Fiscalización",
        "topic": "Función 1",
        "stem": "Una situación laboral completa exige decidir la actuación inicial.",
        "options_A": "Aplicar el procedimiento.",
        "options_B": "Omitir los controles.",
        "options_C": "Delegar sin competencia.",
        "options_D": "",
        "correct_key": "A",
        "difficulty": 8,
    }
    row.update(updates)
    return pd.DataFrame([row])


def test_functional_import_accepts_three_options_and_difficulty_one_to_ten():
    assert validate_import_df(_frame()) == (True, [])


def test_functional_import_rejects_fourth_key_as_correct():
    valid, errors = validate_import_df(_frame(correct_key="D"))
    assert valid is False
    assert any("A, B o C" in error for error in errors)


def test_likert_import_requires_four_options_and_no_key():
    valid, errors = validate_import_df(
        _frame(track="INTEGRIDAD", options_D="Siempre", correct_key="")
    )
    assert valid is True
    assert errors == []

    valid, errors = validate_import_df(
        _frame(track="COMPORTAMENTAL", options_D="", correct_key="A")
    )
    assert valid is False
    assert any("cuarta opción" in error for error in errors)
    assert any("no debe tener clave" in error for error in errors)
