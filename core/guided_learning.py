from __future__ import annotations


def build_guided_learning_brief(questions, learning_minutes: int = 8) -> dict:
    """Create a short pre-practice brief without exposing answers or rationales."""
    questions = list(questions or [])
    if not questions:
        return {}
    primary = questions[0]
    topic = getattr(primary, "topic", None) or "Tema de la sesión"
    macro = getattr(primary, "macro_dominio", None) or getattr(primary, "track", None) or "General"
    sources = []
    for question in questions:
        source = " ".join(str(getattr(question, "source_refs", None) or "").split())
        if source and source not in sources:
            sources.append(source)
    return {
        "topic": topic,
        "macro": macro,
        "minutes": max(3, int(learning_minutes or 8)),
        "objective": (
            f"Al terminar, explica con tus palabras la regla central de {topic} "
            "y cómo la aplicarías ante una situación laboral."
        ),
        "sources": sources[:3],
    }

