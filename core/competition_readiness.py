"""Diagnóstico reutilizable de cobertura para cualquier concurso."""

from dataclasses import dataclass

from sqlalchemy.orm import joinedload

from core.exam_format import build_official_case_blocks
from core.real_exam import blueprint_for_competition
from db.models import CaseStudy, Competition, Question


@dataclass(frozen=True)
class CompetitionReadiness:
    question_count: int
    functional_count: int
    behavioral_count: int
    official_case_count: int
    exam_questions: int
    exam_minutes: int
    next_action: str


def inspect_competition(db, competition_id: int, *, is_pro: bool = False):
    competition = db.get(Competition, competition_id)
    questions = db.query(Question).filter(Question.competition_id == competition_id)
    total = questions.count()
    functional = questions.filter(Question.track == "FUNCIONAL").count()
    behavioral = questions.filter(Question.track == "COMPORTAMENTAL").count()
    cases = db.query(CaseStudy).options(joinedload(CaseStudy.questions)).filter(
        CaseStudy.competition_id == competition_id
    ).all()
    official_cases = len(build_official_case_blocks(cases))
    try:
        blueprint = blueprint_for_competition(
            getattr(competition, "code", None), is_pro=is_pro,
            official_case_count=official_cases,
        )
    except TypeError:
        # Compatibilidad con módulos retenidos por una recarga en caliente de Streamlit.
        blueprint = blueprint_for_competition(getattr(competition, "code", None), is_pro=is_pro)
    available_cases = min(official_cases, blueprint.target_cases)
    exam_questions = available_cases * blueprint.questions_per_case
    if official_cases < 3:
        next_action = "Generar el banco inicial y casos tipo examen."
    elif official_cases < 10:
        next_action = "Ampliar hasta 10 casos para habilitar un examen de 30 preguntas."
    elif total < 100:
        next_action = "Ampliar la cobertura temática del banco."
    else:
        next_action = "Banco listo para práctica y simulacro tipo examen."
    return CompetitionReadiness(
        total, functional, behavioral, official_cases, exam_questions,
        exam_questions * blueprint.minutes_per_question, next_action,
    )
