"""Ayudas socráticas seguras que no dependen de un proveedor de IA."""


def local_socratic_hint(*, topic: str, selected_text: str, source: str = "") -> str:
    focus = topic or "el caso planteado"
    source_line = f" Después contrasta tu criterio con la fuente registrada: {source}." if source else ""
    return (
        f"Antes de cambiar tu respuesta, vuelve a {focus} y pregúntate: "
        "¿qué problema institucional debe resolverse primero?, ¿qué alternativa conserva evidencia "
        "y permite verificar el resultado?, ¿cuál controla mejor el riesgo sin trasladar la "
        f"responsabilidad a un tercero? Tu elección actual plantea: «{selected_text}»."
        f"{source_line}"
    )


def build_socratic_prompt(*, competition: str, stem: str, options: dict,
                          selected_key: str, rationale: str, source: str) -> str:
    return f"""Eres tutor socrático para concursos públicos colombianos.
Concurso y contexto: {competition}
Caso: {stem}
Opciones: {options}
Elección del estudiante: {selected_key}
Fundamento verificado para orientar tu análisis: {rationale}
Fuente registrada: {source}

Formula dos o tres preguntas breves que ayuden al estudiante a revisar su razonamiento.
No reveles la letra correcta, no digas si acertó, no inventes normas y no reemplaces la fuente.
Enfócate en decisión, evidencia, riesgo y resultado. Máximo 90 palabras, en español.
"""
