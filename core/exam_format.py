"""Helpers for the official DIAN 2667 written-test formats."""

from dataclasses import dataclass

FUNCTIONAL_TRACK = "FUNCIONAL"
SITUATIONAL_TYPE = "SITUATIONAL"
FUNCTIONAL_QUESTIONS_PER_CASE = 3
FUNCTIONAL_OPTION_KEYS = ("A", "B", "C")

OFFICIAL_LABEL = "Oficial GOA"
PRACTICE_LABEL = "Practica"
REVIEW_LABEL = "Requiere revision"

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
        if not bool(getattr(question, "is_verified", False)):
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


def _eligible_verified_question(question) -> bool:
    options = getattr(question, "options_json", None)
    return (
        bool(getattr(question, "is_verified", False))
        and str(getattr(question, "track", "")).upper() == FUNCTIONAL_TRACK
        and str(getattr(question, "question_type", SITUATIONAL_TYPE)).upper() == SITUATIONAL_TYPE
        and isinstance(options, dict)
        and tuple(options.keys()) == FUNCTIONAL_OPTION_KEYS
        and getattr(question, "correct_key", None) in FUNCTIONAL_OPTION_KEYS
        and bool(str(getattr(question, "stem", "") or "").strip())
    )


def official_question_groups(case) -> list[list]:
    """Split verified questions from one shared case into complete GOA triplets."""
    eligible = [q for q in (getattr(case, "questions", None) or []) if _eligible_verified_question(q)]
    eligible.sort(key=lambda q: (str(getattr(q, "created_at", "") or ""), str(getattr(q, "question_id", ""))))
    usable = len(eligible) - (len(eligible) % FUNCTIONAL_QUESTIONS_PER_CASE)
    return [
        eligible[index:index + FUNCTIONAL_QUESTIONS_PER_CASE]
        for index in range(0, usable, FUNCTIONAL_QUESTIONS_PER_CASE)
    ]


@dataclass
class OfficialCaseBlock:
    id: str
    title: str
    text: str
    topic: str
    difficulty: int
    questions: list
    competition_id: object = None


def build_official_case_blocks(cases) -> list[OfficialCaseBlock]:
    """Build exam-only views; source cases and questions remain untouched."""
    blocks = []
    for case in cases:
        groups = official_question_groups(case)
        for index, questions in enumerate(groups, start=1):
            suffix = f" - Bloque {index}" if len(groups) > 1 else ""
            blocks.append(
                OfficialCaseBlock(
                    id=f"{getattr(case, 'id', 'case')}-goa-{index}",
                    title=f"{getattr(case, 'title', None) or 'Caso funcional'}{suffix}",
                    text=getattr(case, "text", ""),
                    topic=getattr(case, "topic", ""),
                    difficulty=getattr(case, "difficulty", 2),
                    questions=questions,
                    competition_id=getattr(case, "competition_id", None),
                )
            )
    return blocks


def question_format_status(question) -> str:
    """Classify a question without modifying historical data."""
    case = getattr(question, "case_study", None)
    if case is None:
        return PRACTICE_LABEL
    official_ids = {
        getattr(item, "question_id", None)
        for group in official_question_groups(case)
        for item in group
    }
    if getattr(question, "question_id", None) in official_ids:
        return OFFICIAL_LABEL
    return REVIEW_LABEL