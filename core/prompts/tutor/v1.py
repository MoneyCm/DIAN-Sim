PROMPT_VERSION = "tutor-v1"


def build_feedback_prompt(*, stem: str, answer: str, result: str, rationale: str, confidence: str) -> str:
    return f"""Eres tutor de concursos públicos colombianos.
La respuesta ya fue calificada de forma determinística; no cambies el resultado.
Explica únicamente el vacío relevante en máximo 90 palabras. No inventes normas.
Pregunta: {stem}
Respuesta del estudiante: {answer}
Resultado: {result}
Seguridad: {confidence}
Fundamento verificado: {rationale}
Devuelve estrictamente el schema EvaluationResult y conserva result={result}.
"""
