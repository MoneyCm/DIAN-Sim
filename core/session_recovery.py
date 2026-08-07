"""Funciones puras para recuperar sesiones después de actualizar el banco."""


def recover_question_ids(session_ids, valid_ids, current_position):
    recovered = [question_id for question_id in session_ids if question_id in valid_ids]
    if not recovered:
        return [], 0
    return recovered, min(max(0, current_position), len(recovered) - 1)
