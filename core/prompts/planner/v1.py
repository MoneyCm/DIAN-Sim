PROMPT_VERSION = "planner-v1"


def build_planner_prompt(profile: dict) -> str:
    return f"""Decide entre ask_question, explain_gap o finish_session.
No selecciones preguntas concretas: el motor determinístico lo hará.
Perfil resumido: {profile}
Devuelve exclusivamente TutorDecision.
"""
