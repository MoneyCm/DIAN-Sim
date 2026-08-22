"""Repair stale embedded function labels without losing learning progress.

Stable case identifiers intentionally retain their historical ``fN`` tokens.
The authoritative function is the explicit OPEC scope, so only display/topic
metadata and its derived topic identifiers are migrated.

Usage::

    python scripts/migrations/relabel_stale_opec236769_topics.py
    python scripts/migrations/relabel_stale_opec236769_topics.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.learning.engine import topic_id_for
from core.opec_236769 import function_label
from db.models import (
    CaseStudy,
    OpecLearningEvent,
    OpecProfile,
    OpecTopicState,
    Question,
    QuestionOpecScope,
    Skill,
    TopicMastery,
)
from db.session import SessionLocal


TOPIC_REPAIRS = (
    (
        "goa-236769-f4-priorizacion-pta-apd-02",
        "F4 - Organización de información y propuestas de fiscalización",
        "F7 - Organización de información y propuestas de fiscalización",
        7,
    ),
    (
        "goa-236769-f4-propuesta-apd-directivo-01",
        "F4 - Organización de información y propuestas de fiscalización",
        "F7 - Organización de información y propuestas de fiscalización",
        7,
    ),
    (
        "goa-236769-f9-revision-liquidacion-provisional-01",
        "F9 - Revisión técnica y jurídica de expedientes",
        "F5 - Revisión técnica y jurídica de expedientes",
        5,
    ),
    (
        "goa-236769-f9-revision-expediente-decision-01",
        "F9 - Revisión jurídica, probatoria y de términos",
        "F5 - Revisión jurídica, probatoria y de términos",
        5,
    ),
    (
        "goa-236769-f3-riesgos-indicadores-mejora-01",
        "F3 - Planes, indicadores, riesgos y mejora",
        "F9 - Planes, indicadores, riesgos y mejora",
        9,
    ),
    (
        "goa-236769-f3-seguridad-datos-sistemas-01",
        "F3 - Seguridad de información, datos y sistemas corporativos",
        "F9 - Seguridad de información, datos y sistemas corporativos",
        9,
    ),
    (
        "goa-236769-f3-documentos-pqrs-informes-01",
        "F3 - Gestión documental, peticiones e informes",
        "F9 - Gestión documental, peticiones e informes",
        9,
    ),
)


def _weighted_score(left_score, left_count, right_score, right_count):
    left_count = int(left_count or 0)
    right_count = int(right_count or 0)
    total = left_count + right_count
    if total <= 0:
        return max(float(left_score or 0.0), float(right_score or 0.0))
    return round(
        (
            float(left_score or 0.0) * left_count
            + float(right_score or 0.0) * right_count
        )
        / total,
        2,
    )


def _latest(*values):
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _earliest(*values):
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _migrate_legacy_mastery(db, old_id: str, new_id: str, new_topic: str) -> int:
    changed = 0
    for old in db.query(TopicMastery).filter_by(topic_id=old_id).all():
        target = db.query(TopicMastery).filter_by(
            user_id=old.user_id,
            competition_id=old.competition_id,
            topic_id=new_id,
        ).first()
        if target is None:
            old.topic_id = new_id
            old.topic_label = new_topic
            old.competency = new_topic
        else:
            target.mastery_score = _weighted_score(
                target.mastery_score,
                target.attempts,
                old.mastery_score,
                old.attempts,
            )
            target.attempts = int(target.attempts or 0) + int(old.attempts or 0)
            target.correct_attempts = int(target.correct_attempts or 0) + int(old.correct_attempts or 0)
            target.partial_attempts = int(target.partial_attempts or 0) + int(old.partial_attempts or 0)
            target.importance = max(float(target.importance or 0), float(old.importance or 0))
            target.last_reviewed_at = _latest(target.last_reviewed_at, old.last_reviewed_at)
            target.next_review_at = _earliest(target.next_review_at, old.next_review_at)
            target.updated_at = _latest(target.updated_at, old.updated_at)
            db.delete(old)
        changed += 1
    return changed


def _migrate_opec_states(db, old_id: str, new_id: str, new_topic: str, function: int) -> int:
    changed = 0
    for old in db.query(OpecTopicState).filter_by(topic_id=old_id).all():
        target = db.query(OpecTopicState).filter_by(
            user_id=old.user_id,
            competition_id=old.competition_id,
            user_opec_id=old.user_opec_id,
            topic_id=new_id,
        ).first()
        if target is None:
            old.topic_id = new_id
            old.topic_label = new_topic
            old.function_number = function
        else:
            target.mastery_score = _weighted_score(
                target.mastery_score,
                target.evidence_count,
                old.mastery_score,
                old.evidence_count,
            )
            target.evidence_count = int(target.evidence_count or 0) + int(old.evidence_count or 0)
            target.function_number = function
            target.last_event_at = _latest(target.last_event_at, old.last_event_at)
            target.next_review_at = _earliest(target.next_review_at, old.next_review_at)
            target.updated_at = _latest(target.updated_at, old.updated_at)
            db.delete(old)
        changed += 1
    return changed


def repair(db, *, apply: bool = False) -> dict[str, int]:
    counts = {
        "cases": 0,
        "questions": 0,
        "events": 0,
        "legacy_mastery": 0,
        "opec_states": 0,
        "skills": 0,
    }
    for case_key, old_topic, new_topic, function in TOPIC_REPAIRS:
        case_id = str(uuid.uuid5(uuid.NAMESPACE_URL, case_key))
        case = db.get(CaseStudy, case_id)
        questions = db.query(Question).filter_by(case_id=case_id).all()
        question_ids = [str(question.question_id) for question in questions]

        if question_ids:
            scoped_functions = {
                int(number)
                for (number,) in (
                    db.query(QuestionOpecScope.function_number)
                    .join(OpecProfile, OpecProfile.id == QuestionOpecScope.opec_profile_id)
                    .filter(
                        QuestionOpecScope.question_id.in_(question_ids),
                        OpecProfile.opec_number == "236769",
                    )
                    .all()
                )
                if number is not None
            }
            if scoped_functions and scoped_functions != {function}:
                raise RuntimeError(
                    f"Alcance canónico incompatible para {case_key}: {sorted(scoped_functions)}"
                )

        if case is not None and case.topic != new_topic:
            case.topic = new_topic
            counts["cases"] += 1

        for question in questions:
            if (
                question.topic != new_topic
                or question.competency != new_topic
                or question.micro_competencia != function_label(case_key, new_topic)
            ):
                question.topic = new_topic
                question.competency = new_topic
                question.micro_competencia = function_label(case_key, new_topic)
                counts["questions"] += 1

        old_id = topic_id_for("FUNCIONAL", old_topic, old_topic)
        new_id = topic_id_for("FUNCIONAL", new_topic, new_topic)
        counts["legacy_mastery"] += _migrate_legacy_mastery(
            db, old_id, new_id, new_topic
        )
        counts["opec_states"] += _migrate_opec_states(
            db, old_id, new_id, new_topic, function
        )
        if question_ids:
            events = db.query(OpecLearningEvent).filter(
                OpecLearningEvent.question_id.in_(question_ids),
                OpecLearningEvent.topic_id == old_id,
            ).all()
            for event in events:
                event.topic_id = new_id
                event.topic_label = new_topic
                event.function_number = function
            counts["events"] += len(events)

        skills = db.query(Skill).filter(
            Skill.track == "FUNCIONAL",
            Skill.competency == old_topic,
            Skill.topic == old_topic,
        ).all()
        for skill in skills:
            skill.competency = new_topic
            skill.topic = new_topic
            skill.micro_competencia = function_label(case_key, new_topic)
        counts["skills"] += len(skills)

    if apply:
        db.commit()
    else:
        db.rollback()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        counts = repair(db, apply=args.apply)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"{mode}: {counts}")


if __name__ == "__main__":
    main()
