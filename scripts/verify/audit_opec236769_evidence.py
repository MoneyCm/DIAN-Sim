"""Read-only evidence audit for the canonical OPEC 236769 bank."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.legacy_question_audit import is_safe_for_active_study
from core.source_evidence import assess_source_evidence, precise_source_verification_error
from db.models import (
    OpecProfile,
    Question,
    QuestionCitation,
    QuestionOpecScope,
    QuestionRevision,
)
from db.session import SessionLocal


def audit() -> dict:
    db = SessionLocal()
    try:
        profile = db.query(OpecProfile).filter_by(opec_number="236769").first()
        if profile is None:
            raise RuntimeError("No existe el perfil OPEC 236769.")
        rows = (
            db.query(QuestionOpecScope, Question)
            .join(Question, Question.question_id == QuestionOpecScope.question_id)
            .filter(QuestionOpecScope.opec_profile_id == profile.id)
            .all()
        )
        training = [(scope, question) for scope, question in rows if scope.bank_partition == "training"]
        reserved = [(scope, question) for scope, question in rows if scope.bank_partition == "reserved"]
        training_ids = [question.question_id for _, question in training]
        scoped_ids = [question.question_id for _, question in rows]
        duplicates = [
            question.question_id
            for _, question in training
            if not isinstance(question.options_json, dict)
            or len({str(value).strip() for value in question.options_json.values()})
            != len(question.options_json)
        ]
        distributions = {
            function: dict(Counter(
                question.correct_key
                for scope, question in training
                if scope.function_number == function
            ))
            for function in range(1, 10)
        }
        return {
            "total_scoped": len(rows),
            "training": len(training),
            "reserved": len(reserved),
            "duplicate_training_options": len(duplicates),
            "key_distribution": distributions,
            "nonempty_source_refs": sum(
                bool(str(question.source_refs or "").strip()) for _, question in training
            ),
            "direct_source_anchors": sum(
                assess_source_evidence(question)["status"] == "DIRECT_OFFICIAL_SOURCE"
                for _, question in training
            ),
            "precisely_verified": sum(
                precise_source_verification_error(question) is None
                for _, question in training
            ),
            "safe_for_active_study": sum(
                is_safe_for_active_study(question) for _, question in training
            ),
            "canonical_revisions_training": db.query(QuestionRevision).filter(
                QuestionRevision.question_id.in_(training_ids)
            ).count(),
            "canonical_revisions_all_scoped": db.query(QuestionRevision).filter(
                QuestionRevision.question_id.in_(scoped_ids)
            ).count(),
            "canonical_revision_statuses": dict(Counter(
                status for status, in db.query(QuestionRevision.status).filter(
                    QuestionRevision.question_id.in_(scoped_ids)
                ).all()
            )),
            "canonical_citations_training": db.query(QuestionCitation).filter(
                QuestionCitation.question_id.in_(training_ids)
            ).count(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    result = audit()
    for key, value in result.items():
        print(f"{key}: {value}")
