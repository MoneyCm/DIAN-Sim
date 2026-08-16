"""Canonical Phase 2 learning evidence scoped to one configured OPEC.

Legacy attempt/skill tables remain available for compatibility.  New
diagnostic, training and measurement flows should write here so readiness,
difficulty and error review all consume the same immutable answer events.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from typing import Iterable, Mapping, Sequence

from sqlalchemy import func

from core.error_notebook import (
    TransferEvidence,
    build_error_guidance,
    evaluate_error_resolution,
    normalize_error_category,
)
from core.learning.engine import editorial_question_difficulty, topic_id_for
from core.learning.review_policy import normalize_confidence, review_interval
from core.legacy_question_audit import is_safe_for_active_study
from core.opec_question_context import function_number_for_question
from core.preparation_matrix import load_preparation_blueprint
from core.readiness_gate import (
    BankEvidence,
    ItemResult,
    MeasurementSessionResult,
    ReadinessPolicy,
    evaluate_readiness,
)
from core.source_evidence import has_precise_source_verification
from db.models import (
    ErrorEpisode,
    OpecLearningEvent,
    OpecLearningSession,
    OpecStudyPlan,
    OpecTopicState,
    Question,
    QuestionRevision,
    UserOPEC,
)
from services.question_service import QuestionService


LEARNING_POLICY_VERSION = "learning-evidence-internal-v1"
DIAGNOSTIC_MODE = "diagnostic"
MEASUREMENT_MODE = "measurement"


def utc_now() -> datetime:
    """Return naive UTC for compatibility with the existing DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def _question_revision_hash(question: Question, difficulty: int) -> str:
    payload = {
        "stem": str(question.stem or "").strip(),
        "options": question.options_json or {},
        "correct_key": question.correct_key,
        "rationale": str(question.rationale or "").strip(),
        "difficulty": int(difficulty),
        "question_type": str(question.question_type or "SITUATIONAL").upper(),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_snapshot(question: Question) -> dict:
    report = question.quality_report if isinstance(question.quality_report, dict) else {}
    verification = report.get("source_verification")
    return dict(verification) if isinstance(verification, dict) else {}


def _resolve_opec(
    db,
    *,
    user_id: int,
    competition_id: int | None = None,
    user_opec_id: int | None = None,
) -> UserOPEC:
    query = db.query(UserOPEC).filter(UserOPEC.user_id == int(user_id))
    if user_opec_id is not None:
        query = query.filter(UserOPEC.id == int(user_opec_id))
    else:
        query = query.filter(UserOPEC.is_active.is_(True))
    if competition_id is not None:
        query = query.filter(UserOPEC.competition_id == int(competition_id))
    rows = query.order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc()).all()
    if len(rows) != 1:
        raise ValueError("No existe un único contexto OPEC para registrar aprendizaje.")
    row = rows[0]
    if row.competition_id is None:
        raise ValueError("La OPEC no tiene concurso asociado.")
    return row


def _ensure_current_opec(db, session: OpecLearningSession) -> UserOPEC:
    current = (
        db.query(UserOPEC)
        .filter_by(user_id=session.user_id, is_active=True)
        .order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc())
        .first()
    )
    if (
        current is None
        or current.id != session.user_opec_id
        or current.competition_id != session.competition_id
        or str(current.opec_number) != str(session.opec_number)
    ):
        session.status = "invalid"
        raise ValueError("La OPEC activa cambió; la sesión se invalidó de forma segura.")
    return current


def ensure_question_revision(
    db,
    question: Question,
    *,
    bank_partition: str,
) -> QuestionRevision:
    """Snapshot only a question that already passed the strict study gate."""
    if bank_partition not in {"training", "measurement", "anchor", "reserved"}:
        raise ValueError("Partición de banco no válida.")
    if not is_safe_for_active_study(question):
        raise ValueError("La pregunta no tiene evidencia suficiente para crear una revisión.")
    difficulty = editorial_question_difficulty(question)
    content_hash = _question_revision_hash(question, difficulty)
    existing = (
        db.query(QuestionRevision)
        .filter_by(
            question_id=str(question.question_id),
            content_hash=content_hash,
            status="approved",
            bank_partition=bank_partition,
        )
        .order_by(QuestionRevision.revision_number.desc())
        .first()
    )
    if existing is not None:
        return existing
    next_number = int(
        db.query(func.max(QuestionRevision.revision_number))
        .filter(QuestionRevision.question_id == str(question.question_id))
        .scalar()
        or 0
    ) + 1
    revision = QuestionRevision(
        question_id=str(question.question_id),
        revision_number=next_number,
        content_hash=content_hash,
        stem=question.stem,
        options_json=dict(question.options_json or {}),
        correct_key=question.correct_key,
        rationale=question.rationale,
        difficulty_level=difficulty,
        bank_partition=bank_partition,
        source_snapshot=_source_snapshot(question),
        status="approved",
        change_reason="Instantánea del contenido ya habilitado para evidencia pedagógica.",
        actor="phase2_evidence_service",
        actor_type="system_snapshot",
    )
    db.add(revision)
    db.flush()
    return revision


def start_opec_session(
    db,
    *,
    user_id: int,
    questions: Sequence[Question],
    mode: str,
    bank_partition: str,
    competition_id: int | None = None,
    user_opec_id: int | None = None,
    policy_version: str | None = None,
    blueprint_version: str | None = None,
    feedback_enabled: bool = False,
    aids_used: bool = False,
    now: datetime | None = None,
) -> OpecLearningSession:
    if mode not in {"diagnostic", "training", "measurement", "review"}:
        raise ValueError("Modo de aprendizaje no válido.")
    if bank_partition not in {"training", "measurement", "anchor", "reserved"}:
        raise ValueError("Partición de banco no válida.")
    if mode == MEASUREMENT_MODE and bank_partition != "measurement":
        raise ValueError("Una medición estricta solo puede usar la partición measurement.")
    question_list = list(questions or ())
    if not question_list:
        raise ValueError("La sesión necesita al menos una pregunta.")
    if len({str(question.question_id) for question in question_list}) != len(question_list):
        raise ValueError("La sesión contiene preguntas repetidas.")

    user_opec = _resolve_opec(
        db,
        user_id=user_id,
        competition_id=competition_id,
        user_opec_id=user_opec_id,
    )
    if any(question.competition_id != user_opec.competition_id for question in question_list):
        raise ValueError("La sesión contiene una pregunta de otro concurso.")
    eligible_ids = {
        str(question.question_id)
        for question in QuestionService.get_questions_for_user(
            db,
            user_id,
            competition_id=user_opec.competition_id,
            user_opec=user_opec,
            bank_partitions=(bank_partition,),
        )
    }
    requested_ids = {str(question.question_id) for question in question_list}
    if not requested_ids.issubset(eligible_ids):
        raise ValueError("La sesión contiene una pregunta fuera del alcance OPEC o partición activa.")

    revisions = [
        ensure_question_revision(db, question, bank_partition=bank_partition)
        for question in question_list
    ]
    revision_by_question = {
        str(question.question_id): str(revision.id)
        for question, revision in zip(question_list, revisions)
    }
    function_by_question = {
        str(question.question_id): function_number_for_question(
            question, user_opec.opec_number
        )
        for question in question_list
    }
    case_ids = [
        str(question.case_id)
        for question in question_list
        if getattr(question, "case_id", None)
    ]
    blueprint = load_preparation_blueprint(user_opec.opec_number)
    session = OpecLearningSession(
        user_id=int(user_id),
        competition_id=int(user_opec.competition_id),
        user_opec_id=int(user_opec.id),
        opec_number=str(user_opec.opec_number),
        mode=mode,
        policy_version=(
            policy_version
            or (ReadinessPolicy().version if mode == MEASUREMENT_MODE else LEARNING_POLICY_VERSION)
        ),
        blueprint_version=(
            blueprint_version or blueprint.get("version") or "unversioned-blueprint"
        ),
        bank_partition=bank_partition,
        status="active",
        started_at=now or utc_now(),
        total_questions=len(question_list),
        answered_questions=0,
        feedback_enabled=bool(feedback_enabled),
        aids_used=bool(aids_used),
        question_revision_ids=[str(revision.id) for revision in revisions],
        case_ids=list(dict.fromkeys(case_ids)),
        coverage={
            "question_ids": [str(question.question_id) for question in question_list],
            "revision_by_question": revision_by_question,
            "function_by_question": function_by_question,
            "function_numbers": sorted(
                {
                    number for number in function_by_question.values()
                    if isinstance(number, int)
                }
            ),
        },
    )
    db.add(session)
    db.flush()
    return session


def _canonical_confidence(value: str | None) -> str | None:
    return normalize_confidence(value)


def _novelty_for(db, session: OpecLearningSession, question_id: str) -> str:
    prior = (
        db.query(OpecLearningEvent.id)
        .join(OpecLearningSession)
        .filter(
            OpecLearningEvent.user_id == session.user_id,
            OpecLearningEvent.question_id == question_id,
            OpecLearningSession.competition_id == session.competition_id,
            OpecLearningSession.user_opec_id == session.user_opec_id,
            OpecLearningSession.id != session.id,
        )
        .first()
    )
    return "new" if prior is None else "seen"


def _update_topic_state(
    db,
    *,
    session: OpecLearningSession,
    event: OpecLearningEvent,
    confidence_for_schedule: str | None,
) -> OpecTopicState | None:
    if event.is_correct is None:
        return None
    state = (
        db.query(OpecTopicState)
        .filter_by(
            user_id=session.user_id,
            competition_id=session.competition_id,
            user_opec_id=session.user_opec_id,
            topic_id=event.topic_id,
        )
        .first()
    )
    if state is None:
        state = OpecTopicState(
            user_id=session.user_id,
            competition_id=session.competition_id,
            user_opec_id=session.user_opec_id,
            opec_number=session.opec_number,
            topic_id=event.topic_id,
            topic_label=event.topic_label,
            function_number=event.function_number,
            mastery_score=0.0,
            evidence_count=0,
        )
        db.add(state)
        db.flush()

    current = min(max(float(state.mastery_score or 0.0), 0.0), 100.0)
    target = 100.0 if event.is_correct else 0.0
    # Novel/transfer/measurement evidence receives normal weight. Repetition
    # can reinforce, but has a smaller effect and cannot masquerade as novelty.
    alpha = 0.20 if event.novelty in {"new", "transfer"} or session.mode == "measurement" else 0.10
    state.mastery_score = round(current + alpha * (target - current), 2)
    state.evidence_count = int(state.evidence_count or 0) + 1
    state.last_event_at = event.created_at
    result = "correct" if event.is_correct else "incorrect"
    decision = review_interval(result=result, confidence=confidence_for_schedule)
    state.next_review_at = event.created_at + timedelta(days=decision.interval_days)
    state.updated_at = event.created_at
    return state


def _create_error_episode(
    db,
    *,
    session: OpecLearningSession,
    event: OpecLearningEvent,
    question: Question,
    error_category: str | None,
    user_reasoning: str | None,
) -> ErrorEpisode:
    guidance = build_error_guidance(
        category=error_category,
        user_reasoning=user_reasoning,
        rationale=question.rationale,
        source_reference=question.source_refs,
    )
    interval = review_interval(result="incorrect", confidence=event.confidence)
    episode = ErrorEpisode(
        learning_event_id=event.id,
        user_id=session.user_id,
        competition_id=session.competition_id,
        user_opec_id=session.user_opec_id,
        opec_number=session.opec_number,
        question_id=event.question_id,
        question_revision_id=event.question_revision_id,
        category=normalize_error_category(guidance.category),
        user_reasoning=guidance.user_reasoning,
        failure_reason=guidance.why_it_failed,
        rule_to_remember=guidance.rule_to_remember,
        source_reference={
            "declared": guidance.source_to_review,
            "verification": _source_snapshot(question),
        },
        micro_lesson=guidance.micro_lesson,
        reinforcement_question_ids=[],
        status="scheduled",
        next_review_at=event.created_at + timedelta(days=interval.interval_days),
        created_at=event.created_at,
        updated_at=event.created_at,
    )
    db.add(episode)
    return episode


def record_opec_event(
    db,
    *,
    session_id: str,
    user_id: int,
    question_id: str,
    chosen_key: str | None,
    confidence: str | None = None,
    time_sec: int | None = None,
    novelty: str | None = None,
    error_category: str | None = None,
    user_reasoning: str | None = None,
    now: datetime | None = None,
) -> OpecLearningEvent:
    session = db.get(OpecLearningSession, str(session_id))
    if session is None or session.user_id != int(user_id) or session.status != "active":
        raise ValueError("No existe una sesión OPEC activa para este usuario.")
    _ensure_current_opec(db, session)
    if time_sec is not None and int(time_sec) < 0:
        raise ValueError("El tiempo de respuesta no puede ser negativo.")
    coverage = session.coverage if isinstance(session.coverage, dict) else {}
    allowed_ids = {str(value) for value in coverage.get("question_ids", [])}
    if str(question_id) not in allowed_ids:
        raise ValueError("La pregunta no pertenece a la instantánea de esta sesión.")
    if db.query(OpecLearningEvent).filter_by(
        session_id=session.id, question_id=str(question_id)
    ).first():
        raise ValueError("La pregunta ya fue registrada en esta sesión.")
    question = db.get(Question, str(question_id))
    if question is None or question.competition_id != session.competition_id:
        raise ValueError("La pregunta ya no pertenece al concurso de la sesión.")
    revision_id = str((coverage.get("revision_by_question") or {}).get(str(question_id), ""))
    revision = db.get(QuestionRevision, revision_id)
    if revision is None or revision.question_id != str(question_id):
        raise ValueError("La revisión inmutable de la pregunta no está disponible.")
    observed_at = now or utc_now()
    canonical_confidence = _canonical_confidence(confidence)
    question_type = str(question.question_type or "SITUATIONAL").upper()
    is_likert = question_type in {"LIKERT", "SELF_REPORT", "AUTORREPORTE"}
    is_correct = None if is_likert else bool(chosen_key == revision.correct_key)
    event_novelty = str(novelty or _novelty_for(db, session, str(question_id))).lower()
    if event_novelty not in {"new", "seen", "repeated", "transfer", "unknown"}:
        raise ValueError("Estado de exposición no válido.")
    precise_source = has_precise_source_verification(question)
    verification = _source_snapshot(question)
    source_current = str(verification.get("status", "")).casefold() in {
        "official_current",
        "official_verified",
    }
    event = OpecLearningEvent(
        session_id=session.id,
        user_id=session.user_id,
        question_id=str(question.question_id),
        case_id=str(question.case_id) if question.case_id else None,
        question_revision_id=revision.id,
        function_number=(coverage.get("function_by_question") or {}).get(str(question_id)),
        topic_id=topic_id_for(question.track, question.competency, question.topic),
        topic_label=question.topic or "Sin tema",
        is_correct=is_correct,
        confidence=canonical_confidence,
        time_sec=int(time_sec) if time_sec is not None else None,
        novelty=event_novelty,
        editorial_difficulty=int(revision.difficulty_level or editorial_question_difficulty(question)),
        source_verified=precise_source,
        source_current=source_current,
        evidence_complete=precise_source and source_current,
        created_at=observed_at,
    )
    db.add(event)
    db.flush()
    session.answered_questions = (
        db.query(OpecLearningEvent)
        .filter(OpecLearningEvent.session_id == session.id)
        .count()
    )
    _update_topic_state(
        db,
        session=session,
        event=event,
        confidence_for_schedule=canonical_confidence,
    )
    if is_correct is False:
        _create_error_episode(
            db,
            session=session,
            event=event,
            question=question,
            error_category=error_category,
            user_reasoning=user_reasoning,
        )
    return event


def finalize_opec_session(
    db,
    *,
    session_id: str,
    user_id: int,
    now: datetime | None = None,
    require_complete: bool | None = None,
) -> OpecLearningSession:
    session = db.get(OpecLearningSession, str(session_id))
    if session is None or session.user_id != int(user_id) or session.status != "active":
        raise ValueError("No existe una sesión OPEC activa para finalizar.")
    _ensure_current_opec(db, session)
    events = (
        db.query(OpecLearningEvent)
        .filter_by(session_id=session.id)
        .order_by(OpecLearningEvent.created_at, OpecLearningEvent.id)
        .all()
    )
    session.answered_questions = len(events)
    strict = session.mode == MEASUREMENT_MODE if require_complete is None else require_complete
    if strict and len(events) != session.total_questions:
        session.status = "invalid"
        raise ValueError("Una medición incompleta no puede registrarse como completada.")
    scored = [event for event in events if event.is_correct is not None]
    session.score = (
        round(sum(event.is_correct is True for event in scored) / len(scored) * 100.0, 4)
        if scored else None
    )
    by_function: dict[str, dict[str, int]] = {}
    for event in scored:
        key = str(event.function_number) if event.function_number is not None else "unmapped"
        bucket = by_function.setdefault(key, {"correct": 0, "total": 0})
        bucket["total"] += 1
        bucket["correct"] += int(event.is_correct is True)
    coverage = dict(session.coverage or {})
    coverage["results_by_function"] = by_function
    coverage["functional_scored_items"] = len(scored)
    session.coverage = coverage
    session.completed_at = now or utc_now()
    session.status = "completed"
    return session


def refresh_error_episode(db, episode: ErrorEpisode, *, now: datetime | None = None) -> ErrorEpisode:
    events = (
        db.query(OpecLearningEvent)
        .join(OpecLearningSession)
        .filter(
            OpecLearningEvent.user_id == episode.user_id,
            OpecLearningSession.competition_id == episode.competition_id,
            OpecLearningSession.user_opec_id == episode.user_opec_id,
            OpecLearningEvent.created_at > episode.created_at,
        )
        .order_by(OpecLearningEvent.created_at)
        .all()
    )
    transfer = [
        TransferEvidence(
            question_id=event.question_id,
            revision_id=event.question_revision_id,
            correct=event.is_correct,
            occurred_at=event.created_at,
            is_novel=event.novelty in {"new", "transfer"},
            question_type=str(getattr(db.get(Question, event.question_id), "question_type", "SITUATIONAL")),
        )
        for event in events
    ]
    result = evaluate_error_resolution(
        original_question_id=episode.question_id,
        opened_at=episode.created_at,
        evidence=transfer,
    )
    episode.transfer_evidence = {
        "qualifying_count": result.qualifying_transfer_count,
        "required_count": result.required_transfer_count,
        "earliest_valid_at": result.earliest_valid_at.isoformat(),
        "reason": result.reason,
    }
    if result.overcome:
        qualifying_ids = {
            (item.question_id, item.revision_id)
            for item in transfer
            if item.correct is True
            and item.is_novel
            and item.question_id != episode.question_id
            and item.occurred_at >= result.earliest_valid_at
            and str(item.question_type).upper() == "SITUATIONAL"
        }
        qualifying_events = [
            event for event in events
            if (event.question_id, event.question_revision_id) in qualifying_ids
        ]
        episode.transfer_event_id = qualifying_events[-1].id
        episode.reinforcement_question_ids = list(
            dict.fromkeys(event.question_id for event in qualifying_events)
        )
        episode.status = "overcome"
        episode.overcome_at = now or utc_now()
    elif episode.status not in {"dismissed", "overcome"}:
        episode.status = "transfer_pending"
    return episode


def _measurement_result(db, session: OpecLearningSession) -> MeasurementSessionResult:
    events = (
        db.query(OpecLearningEvent, Question)
        .join(Question, Question.question_id == OpecLearningEvent.question_id)
        .filter(OpecLearningEvent.session_id == session.id)
        .order_by(OpecLearningEvent.created_at, OpecLearningEvent.id)
        .all()
    )
    items = tuple(
        ItemResult(
            revision_id=event.question_revision_id,
            case_id=event.case_id or "",
            function_number=event.function_number,
            is_correct=event.is_correct,
            track=question.track,
            question_type=question.question_type,
        )
        for event, question in events
    )
    return MeasurementSessionResult(
        session_id=session.id,
        user_id=session.user_id,
        competition_id=session.competition_id,
        opec_number=session.opec_number,
        policy_version=session.policy_version,
        blueprint_version=session.blueprint_version or "",
        started_at=session.started_at,
        completed_at=session.completed_at,
        items=items,
        bank_partition=session.bank_partition,
        completed=session.status == "completed",
        feedback_enabled=session.feedback_enabled,
        aids_used=session.aids_used,
        functional_score=session.score,
    )


def evaluate_opec_readiness(
    db,
    *,
    user_id: int,
    user_opec_id: int | None = None,
    policy: ReadinessPolicy | None = None,
    as_of: datetime | str | None = None,
):
    policy = policy or ReadinessPolicy()
    user_opec = _resolve_opec(db, user_id=user_id, user_opec_id=user_opec_id)
    rows = (
        db.query(OpecLearningSession)
        .filter_by(
            user_id=user_id,
            competition_id=user_opec.competition_id,
            user_opec_id=user_opec.id,
            mode=MEASUREMENT_MODE,
        )
        .order_by(OpecLearningSession.completed_at.desc())
        .all()
    )
    structured = [_measurement_result(db, row) for row in rows]
    event_rows = (
        db.query(OpecLearningEvent)
        .join(OpecLearningSession)
        .filter(
            OpecLearningSession.user_id == user_id,
            OpecLearningSession.user_opec_id == user_opec.id,
            OpecLearningSession.mode == MEASUREMENT_MODE,
        )
        .all()
    )
    trusted_ids = frozenset(
        event.question_revision_id for event in event_rows if event.evidence_complete
    )
    all_trusted = bool(event_rows) and all(event.evidence_complete for event in event_rows)
    evidence = BankEvidence(
        sources_verified=all_trusted,
        measurement_bank_trusted=all_trusted,
        trusted_revision_ids=trusted_ids,
        note="Evidencia capturada al responder cada revisión inmutable.",
    )
    return evaluate_readiness(
        structured,
        bank_evidence=evidence,
        policy=policy,
        retention=None,
        as_of=as_of,
    )


__all__ = [
    "DIAGNOSTIC_MODE",
    "LEARNING_POLICY_VERSION",
    "MEASUREMENT_MODE",
    "ensure_question_revision",
    "evaluate_opec_readiness",
    "finalize_opec_session",
    "record_opec_event",
    "refresh_error_episode",
    "start_opec_session",
]
