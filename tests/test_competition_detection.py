from core.competition_detection import (
    competition_code_from_name,
    competition_matches,
    detect_competition_from_simo,
)


SAMPLE = """Vigencia salarial: 2025  ADRES - ABIERTO.  Cierre de inscripciones: 2026-07-23"""


def test_detects_adres_process_from_simo_header():
    detected = detect_competition_from_simo(SAMPLE)
    assert detected == {"name": "ADRES - ABIERTO", "entity": "ADRES", "code": "ADRES-ABIERTO"}


def test_detected_process_does_not_match_uapa():
    detected = detect_competition_from_simo(SAMPLE)
    assert not competition_matches(
        detected, selected_name="Alimentación Escolar - Abierto", selected_entity="UApA"
    )
    assert competition_matches(detected, selected_name="ADRES - ABIERTO", selected_entity="ADRES")


def test_code_normalizes_accents_and_symbols():
    assert competition_code_from_name("Nación 6 - Abierto") == "NACION-6-ABIERTO"
