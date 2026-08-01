"""Helpers for the official DIAN 2667 written-test formats."""

FUNCTIONAL_TRACK = "FUNCIONAL"
SITUATIONAL_TYPE = "SITUATIONAL"
FUNCTIONAL_QUESTIONS_PER_CASE = 3
FUNCTIONAL_OPTION_KEYS = ("A", "B", "C")

LIKERT_OPTIONS = (
    "1 - Totalmente en desacuerdo",
    "2 - En desacuerdo",
    "3 - De acuerdo",
    "4 - Totalmente de acuerdo",
)


def is_official_functional_case(case) -> bool:
    questions = list(getattr(case, "questions", None) or [])
    if len(questions) != FUNCTIONAL_QUESTIONS_PER_CASE:
        return False
    for question in questions:
        options = getattr(question, "options_json", None)
        if str(getattr(question, "track", "")).upper() != FUNCTIONAL_TRACK:
            return False
        if str(getattr(question, "question_type", SITUATIONAL_TYPE)).upper() != SITUATIONAL_TYPE:
            return False
        if not isinstance(options, dict) or tuple(options.keys()) != FUNCTIONAL_OPTION_KEYS:
            return False
        if getattr(question, "correct_key", None) not in FUNCTIONAL_OPTION_KEYS:
            return False
        if not str(getattr(question, "stem", "") or "").strip():
            return False
    return bool(str(getattr(case, "text", "") or "").strip())


def is_official_functional_payload(payload: dict) -> bool:
    """Validate the JSON returned by an LLM before persistence."""
    if not isinstance(payload, dict) or not str(payload.get("text", "")).strip():
        return False
    questions = payload.get("questions")
    if not isinstance(questions, list) or len(questions) != FUNCTIONAL_QUESTIONS_PER_CASE:
        return False
    for question in questions:
        options = question.get("options") if isinstance(question, dict) else None
        if not isinstance(question, dict) or str(question.get("track", "")).upper() != FUNCTIONAL_TRACK:
            return False
        if not isinstance(options, dict) or tuple(options.keys()) != FUNCTIONAL_OPTION_KEYS:
            return False
        if question.get("correct_key") not in FUNCTIONAL_OPTION_KEYS:
            return False
        if not str(question.get("stem", "")).strip():
            return False
    return True