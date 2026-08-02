from collections import Counter

from scripts.data.repair_curated_macrodomains import ALL_CURATED_CASES, macro_domain


def test_catalog_has_47_complete_curated_cases():
    assert len(ALL_CURATED_CASES) == 47
    assert sum(len(case["questions"]) for case in ALL_CURATED_CASES) == 141
    assert all(len(case["questions"]) == 3 for case in ALL_CURATED_CASES)


def test_real_macrodomain_distribution_is_explicit():
    counts = Counter(macro_domain(case) for case in ALL_CURATED_CASES)
    assert counts == {
        "Tributario": 20,
        "Aduanero": 10,
        "Cambiario": 8,
        "Transversal": 9,
    }
