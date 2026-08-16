"""Diagnóstico reutilizable de cobertura para un concurso u OPEC concreta."""

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.orm import joinedload

from core.exam_format import build_official_case_blocks
from core.question_opec_scope import question_matches_opec
from core.real_exam import blueprint_for_competition
from db.models import (
    CaseOpecScope,
    CaseStudy,
    Competition,
    OpecProfile,
    Question,
    QuestionOpecScope,
)


_STUDY_PARTITIONS = ("training",)


@dataclass(frozen=True)
class CompetitionReadiness:
    question_count: int
    functional_count: int
    behavioral_count: int
    official_case_count: int
    exam_questions: int
    exam_minutes: int
    next_action: str
    enabled_question_count: int = 0
    pending_review_count: int = 0

    @property
    def reviewed_practice_case_count(self) -> int:
        """Cases admitted to internal practice, not validated exam measures."""
        return self.official_case_count


def _canonical_opec_scope(db, competition_id: int, opec_number: object):
    """Return authoritative question/case ids, or ``None`` for legacy data.

    A canonical profile with zero associations intentionally returns two empty
    sets: once an OPEC has been registered in the additive scope schema, text
    matching must not silently repopulate it with questions from another job.
    """
    try:
        inspector = inspect(db.connection())
        required_tables = {
            OpecProfile.__tablename__,
            QuestionOpecScope.__tablename__,
            CaseOpecScope.__tablename__,
        }
        if not required_tables.issubset(set(inspector.get_table_names())):
            return None
    except (AttributeError, TypeError):
        # Compatibility with light-weight fake sessions and pre-migration DBs.
        return None

    profile = db.query(OpecProfile).filter_by(
        competition_id=competition_id,
        opec_number=str(opec_number),
    ).first()
    if profile is None:
        return None

    question_ids = {
        row[0]
        for row in db.query(QuestionOpecScope.question_id).filter(
            QuestionOpecScope.opec_profile_id == profile.id,
            QuestionOpecScope.bank_partition.in_(_STUDY_PARTITIONS),
        ).all()
    }
    case_ids = {
        row[0]
        for row in db.query(CaseOpecScope.case_id).filter(
            CaseOpecScope.opec_profile_id == profile.id,
        ).all()
    }
    return question_ids, case_ids


def _scoped_inventory(db, competition_id: int, opec_number: object | None):
    questions = db.query(Question).filter(
        Question.competition_id == competition_id
    ).all()
    cases = db.query(CaseStudy).options(joinedload(CaseStudy.questions)).filter(
        CaseStudy.competition_id == competition_id
    ).all()
    target = str(opec_number or "").strip()
    if not target:
        return questions, cases, None

    canonical_scope = _canonical_opec_scope(db, competition_id, target)
    if canonical_scope is not None:
        question_ids, case_ids = canonical_scope
        return (
            [item for item in questions if item.question_id in question_ids],
            [item for item in cases if item.id in case_ids],
            question_ids,
        )

    scoped_questions = [
        item for item in questions if question_matches_opec(item, target)
    ]
    scoped_ids = {item.question_id for item in scoped_questions}
    # In the legacy schema the questions are the only trustworthy scope
    # evidence. Cases are retained provisionally and their blocks are checked
    # below so a mixed triplet can never count as ready.
    return scoped_questions, cases, scoped_ids


def inspect_competition(
    db,
    competition_id: int,
    *,
    is_pro: bool = False,
    opec_number: object | None = None,
):
    competition = db.get(Competition, competition_id)
    questions, cases, scoped_question_ids = _scoped_inventory(
        db, competition_id, opec_number
    )
    total = len(questions)
    functional = sum(item.track == "FUNCIONAL" for item in questions)
    behavioral = sum(item.track == "COMPORTAMENTAL" for item in questions)
    enabled = sum(bool(item.is_verified) for item in questions)
    pending_review = total - enabled
    reviewed_blocks = build_official_case_blocks(cases)
    if scoped_question_ids is not None:
        reviewed_blocks = [
            block for block in reviewed_blocks
            if block.questions
            and all(
                question.question_id in scoped_question_ids
                for question in block.questions
            )
        ]
    reviewed_practice_cases = len(reviewed_blocks)
    try:
        blueprint = blueprint_for_competition(
            getattr(competition, "code", None),
            is_pro=is_pro,
            reviewed_case_count=reviewed_practice_cases,
        )
    except TypeError:
        # Compatibilidad con módulos retenidos por una recarga en caliente de Streamlit.
        try:
            blueprint = blueprint_for_competition(
                getattr(competition, "code", None),
                is_pro=is_pro,
                official_case_count=reviewed_practice_cases,
            )
        except TypeError:
            blueprint = blueprint_for_competition(
                getattr(competition, "code", None), is_pro=is_pro
            )
    available_cases = min(reviewed_practice_cases, blueprint.target_cases)
    exam_questions = available_cases * blueprint.questions_per_case
    if reviewed_practice_cases < 3:
        next_action = "Generar el banco inicial y casos PJS de práctica."
    elif reviewed_practice_cases < 10:
        next_action = (
            "Ampliar hasta la meta editorial de 10 casos PJS "
            "para una sesión provisional de 30 preguntas."
        )
    elif total < 100:
        next_action = "Ampliar la cobertura temática del banco."
    elif pending_review:
        next_action = f"Revisar {pending_review} pregunta(s) provisional(es) antes de habilitarlas."
    else:
        next_action = "Banco listo para práctica y sesión PJS cronometrada."
    return CompetitionReadiness(
        total, functional, behavioral, reviewed_practice_cases, exam_questions,
        exam_questions * blueprint.minutes_per_question, next_action,
        enabled, pending_review,
    )
