"""Helpers for reviewed situational-practice case blocks.

The label below describes the app's internal quality gate.  It is not a
statement that the CNSC has published or endorsed an identical exam format.
"""

from dataclasses import dataclass

from core.source_evidence import has_precise_source_verification

FUNCTIONAL_TRACK = "FUNCIONAL"
SITUATIONAL_TYPE = "SITUATIONAL"
FUNCTIONAL_QUESTIONS_PER_CASE = 3
PJS_MAX_QUESTIONS_PER_CASE = 3
FUNCTIONAL_OPTION_KEYS = ("A", "B", "C")

OFFICIAL_LABEL = "Caso situacional revisado"
PRACTICE_LABEL = "Practica"
REVIEW_LABEL = "Requiere revision"
TRUSTED_REVIEW_LABELS = {"human_source_grounded", "source_grounded"}

LIKERT_OPTIONS = (
    "1 - Totalmente en desacuerdo",
    "2 - En desacuerdo",
    "3 - De acuerdo",
    "4 - Totalmente de acuerdo",
)


def has_source_grounded_review(question) -> bool:
    report = getattr(question, "quality_report", None)
    return isinstance(report, dict) and report.get("review") in TRUSTED_REVIEW_LABELS


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
        if not has_source_grounded_review(question):
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
        and has_source_grounded_review(question)
        and str(getattr(question, "track", "")).upper() == FUNCTIONAL_TRACK
        and str(getattr(question, "question_type", SITUATIONAL_TYPE)).upper() == SITUATIONAL_TYPE
        and isinstance(options, dict)
        and tuple(options.keys()) == FUNCTIONAL_OPTION_KEYS
        and getattr(question, "correct_key", None) in FUNCTIONAL_OPTION_KEYS
        and bool(str(getattr(question, "stem", "") or "").strip())
    )


def _eligible_trusted_pjs_question(question) -> bool:
    """Return whether an item is safe for a measurement-style PJS block.

    The historical ``is_verified`` flag and a review label are not enough:
    measurement content also needs an exact official locator, supporting
    excerpt, currency check, date and reviewer in ``source_verification``.
    """
    return _eligible_verified_question(question) and has_precise_source_verification(
        question
    )


def trusted_pjs_question_groups(
    case,
    *,
    eligible_question_ids: set[str] | None = None,
) -> list[list]:
    """Build official-methodology PJS groups of one to three trusted items.

    CNSC LP-004-2026 permits *up to* three prompts per shared situation.  The
    older editorial factory still creates triplets, but a valid final group is
    not discarded merely because it contains one or two items.
    """
    eligible = []
    for question in getattr(case, "questions", None) or []:
        question_id = str(getattr(question, "question_id", "") or "")
        if eligible_question_ids is not None and question_id not in eligible_question_ids:
            continue
        if _eligible_trusted_pjs_question(question):
            eligible.append(question)
    eligible.sort(
        key=lambda question: (
            str(getattr(question, "created_at", "") or ""),
            str(getattr(question, "question_id", "")),
        )
    )
    return [
        eligible[index:index + PJS_MAX_QUESTIONS_PER_CASE]
        for index in range(0, len(eligible), PJS_MAX_QUESTIONS_PER_CASE)
    ]


def is_trusted_pjs_case(case) -> bool:
    """Validate a previously built measurement block without mutating it."""
    questions = list(getattr(case, "questions", None) or [])
    return (
        bool(str(getattr(case, "text", "") or "").strip())
        and 1 <= len(questions) <= PJS_MAX_QUESTIONS_PER_CASE
        and all(_eligible_trusted_pjs_question(question) for question in questions)
    )


def official_question_groups(case) -> list[list]:
    """Split verified questions from one shared scenario into complete triplets."""
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
    opec_number: str | None = None
    bank_partition: str | None = None


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


def build_trusted_pjs_case_blocks(
    cases,
    *,
    eligible_question_ids: set[str] | None = None,
    opec_number: object = None,
    bank_partition: str = "measurement",
) -> list[OfficialCaseBlock]:
    """Build non-destructive PJS blocks for the isolated measurement bank."""
    blocks = []
    for case in cases:
        groups = trusted_pjs_question_groups(
            case,
            eligible_question_ids=eligible_question_ids,
        )
        for index, questions in enumerate(groups, start=1):
            suffix = f" - Bloque {index}" if len(groups) > 1 else ""
            blocks.append(
                OfficialCaseBlock(
                    id=f"{getattr(case, 'id', 'case')}-pjs-{index}",
                    title=f"{getattr(case, 'title', None) or 'Caso funcional'}{suffix}",
                    text=getattr(case, "text", ""),
                    topic=getattr(case, "topic", ""),
                    difficulty=getattr(case, "difficulty", 2),
                    questions=questions,
                    competition_id=getattr(case, "competition_id", None),
                    opec_number=str(opec_number or "").strip() or None,
                    bank_partition=bank_partition,
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
