from scripts.data.seed_curated_gap_cases_phase10_plus import PHASES_10_TO_16, macro_domain


def test_incremental_seed_contains_22_complete_cases():
    assert len(PHASES_10_TO_16) == 22
    assert sum(len(case["questions"]) for case in PHASES_10_TO_16) == 66
    assert all(len(case["questions"]) == 3 for case in PHASES_10_TO_16)


def test_incremental_seed_assigns_all_real_macrodomains():
    domains = {macro_domain(case) for case in PHASES_10_TO_16}
    assert domains == {"Tributario", "Aduanero", "Cambiario", "Transversal"}
    assert macro_domain(next(case for case in PHASES_10_TO_16 if "f4-propuesta-apd" in case["id"])) == "Aduanero"
    assert macro_domain(next(case for case in PHASES_10_TO_16 if "prueba-exterior" in case["id"])) == "Cambiario"
