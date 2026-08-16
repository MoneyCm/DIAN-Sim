from pathlib import Path

from core.profiles import PROFILES


def test_opec_236769_profile_keeps_only_traceable_stable_facts():
    profile = PROFILES["Gestor III (OPEC 236769)"]

    assert profile["source_status"] == "official_verified"
    assert profile["source_url"].startswith("https://www.dian.gov.co/")
    assert "salary" not in profile
    assert "vacancies" not in profile
    assert "registration_closing" not in profile
    assert profile["behavioral_competencies"] == [
        "Comportamiento Ético - nivel 4",
        "Adaptabilidad - nivel 3",
        "Comunicación Efectiva - nivel 3",
        "Trabajo en Equipo - nivel 3",
    ]


def test_practice_page_uses_the_canonical_profile_without_a_stale_fallback():
    source = Path("app/pages/1_Nuevo_Simulacro.py").read_text(encoding="utf-8-sig")

    assert "from core.profiles import PROFILES, get_profile_topics" in source
    assert "salary_validity" not in source
    assert "registration_closing" not in source
