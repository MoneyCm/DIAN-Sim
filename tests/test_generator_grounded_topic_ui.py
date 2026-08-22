from pathlib import Path


SOURCE = Path("app/pages/4_Generador_IA.py").read_text(encoding="utf-8")


def test_generator_does_not_default_topic_to_unrelated_job_title():
    assert 'st.session_state.get("ai_default_topic", "")' in SOURCE
    assert "Tema normativo sustentado por la fuente (opcional)" in SOURCE
    assert 'st.session_state.get("ai_default_topic", "Gestor II")' not in SOURCE
