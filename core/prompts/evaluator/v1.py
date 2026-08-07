PROMPT_VERSION = "evaluator-v1"


def build_evaluation_prompt(*, question: str, expected: str, answer: str) -> str:
    return f"""Evalúa una respuesta abierta sin modificar datos ni ejecutar herramientas.
Usa correct, partial o incorrect; score entre 0 y 1 y uno de los tipos de error permitidos.
Pregunta: {question}
Criterio esperado: {expected}
Respuesta: {answer}
Devuelve exclusivamente EvaluationResult.
"""
