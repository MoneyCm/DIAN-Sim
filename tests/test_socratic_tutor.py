from core.socratic_tutor import build_socratic_prompt, local_socratic_hint


def test_local_hint_is_useful_without_revealing_correct_answer():
    hint = local_socratic_hint(topic="Arquitectura empresarial", selected_text="Comprar de inmediato")
    assert "Arquitectura empresarial" in hint
    assert "Comprar de inmediato" in hint
    assert "respuesta correcta" not in hint.lower()
    assert "fuente exacta debe verificarse" in hint.lower()


def test_prompt_uses_active_context_and_forbids_answer_disclosure():
    prompt = build_socratic_prompt(
        competition="UApA", stem="Caso TI", options={"A": "Uno", "B": "Dos", "C": "Tres"},
        selected_key="B", rationale="Fundamento", source="PETI",
    )
    assert "UApA" in prompt
    assert "Elección del estudiante: B" in prompt
    assert "No reveles la letra correcta" in prompt
