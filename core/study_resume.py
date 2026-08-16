"""Persistence helpers for resuming an interrupted ordinary study practice.

The public ``*_daily_run`` names are kept for compatibility with existing
callers and stored configuration keys.  The payload itself is version-tolerant
and now distinguishes the kind and mode of the practice being resumed.
Diagnostic and measurement sessions are evidence-taking workflows, not
ordinary practice, and are deliberately excluded from this persistence path.
"""

from __future__ import annotations

import json
import re
import time
import uuid

from db.models import Configuration, UserOPEC


class NonResumableStudyRunError(ValueError):
    """Raised when evidence-taking sessions reach the practice resume path."""


class StudyRunConflictError(RuntimeError):
    """Raised when a stale browser tab tries to replace a newer saved run."""


def _normalized_token(value: object, default: str = "") -> str:
    return str(value or default).strip().lower()


def is_resumable_practice(
    session_kind: object,
    practice_mode: object | None = None,
) -> bool:
    """Return whether a session belongs to the ordinary resumable workflow.

    ``practice`` is the historical session kind used by manual/custom
    practices, so it is accepted only when its explicit mode is ``custom``.
    Denials are evaluated first because an old diagnostic can also carry that
    historical custom mode.
    """
    kind = _normalized_token(session_kind, "daily")
    mode = _normalized_token(practice_mode)
    evidence_tokens = {"diagnostic", "measurement"}
    if evidence_tokens.intersection(kind.split("_")) or evidence_tokens.intersection(
        mode.split("_")
    ):
        return False
    return (
        kind == "daily"
        or kind == "custom"
        or kind.startswith("training_")
        or (kind == "practice" and mode == "custom")
    )


def _require_resumable(payload: dict) -> None:
    if not is_resumable_practice(
        payload.get("session_kind"), payload.get("practice_mode")
    ):
        raise NonResumableStudyRunError(
            "Las sesiones diagnósticas o de medición no se pueden reanudar."
        )


def _normalize_opec_number(value: object) -> str | None:
    """Return a stable key token for an OPEC number."""
    if value is None:
        return None
    raw = str(value).strip()
    digits = "".join(re.findall(r"\d", raw))
    return digits or raw.lower() or None


def _normalize_competition_id(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _active_context(
    db,
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> tuple[int | None, str | None]:
    """Resolve an explicit or active study context without crossing users."""
    resolved_competition = _normalize_competition_id(competition_id)
    resolved_opec = _normalize_opec_number(opec_number)
    if resolved_competition is not None and resolved_opec is not None:
        return resolved_competition, resolved_opec

    active = (
        db.query(UserOPEC)
        .filter_by(user_id=int(user_id), is_active=True)
        .order_by(UserOPEC.updated_at.desc(), UserOPEC.id.desc())
        .first()
    )
    if active is None:
        return resolved_competition, resolved_opec

    active_competition = _normalize_competition_id(active.competition_id)
    active_opec = _normalize_opec_number(active.opec_number)
    if resolved_competition is None and (
        resolved_opec is None or resolved_opec == active_opec
    ):
        resolved_competition = active_competition
    if resolved_opec is None and (
        resolved_competition is None or resolved_competition == active_competition
    ):
        resolved_opec = active_opec
    return resolved_competition, resolved_opec


def _key(
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> str:
    """Build a context key while preserving the historical user-only key."""
    base = f"active_daily_run:{int(user_id)}"
    competition_id = _normalize_competition_id(competition_id)
    opec_number = _normalize_opec_number(opec_number)
    if competition_id is None and opec_number is None:
        return base
    return f"{base}:competition:{competition_id or 'none'}:opec:{opec_number or 'none'}"


def normalize_daily_run(payload: dict) -> dict:
    session_kind = _normalized_token(payload.get("session_kind"), "daily")
    default_practice_mode = (
        session_kind.removeprefix("training_")
        if session_kind.startswith("training_")
        else "custom" if session_kind in {"practice", "custom"}
        else "daily" if session_kind == "daily"
        else session_kind
    )
    practice_mode = _normalized_token(
        payload.get("practice_mode"), default_practice_mode
    )
    question_ids = [str(item) for item in payload.get("question_ids", []) if item]
    answers = {
        str(key): str(value) for key, value in (payload.get("answers") or {}).items()
        if key and value
    }
    checked = {
        str(key): bool(value) for key, value in (payload.get("checked_answers") or {}).items()
        if key and value
    }
    confidences = {
        str(key): str(value) for key, value in (payload.get("confidences") or {}).items()
        if key and value in {"guess", "unsure", "confident"}
    }
    error_types = {
        str(key): str(value) for key, value in (payload.get("error_types") or {}).items()
        if key and value
    }
    error_reasoning = {
        str(key): str(value).strip()
        for key, value in (payload.get("error_reasoning") or {}).items()
        if key and str(value).strip()
    }
    marked_for_review = list(dict.fromkeys(
        str(value)
        for value in payload.get("marked_for_review", [])
        if str(value).strip()
    ))
    question_times = {
        str(key): max(0, int(value))
        for key, value in (payload.get("question_times") or {}).items()
        if key and str(value).lstrip("-").isdigit()
    }
    current_idx = max(0, min(int(payload.get("current_idx", 0)), max(len(question_ids) - 1, 0)))
    started_at = float(payload.get("started_at", time.time()))
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        legacy_identity = json.dumps(
            {
                "session_kind": session_kind,
                "practice_mode": practice_mode,
                "started_at": started_at,
                "question_ids": question_ids,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, legacy_identity))
    return {
        "run_id": run_id,
        "session_kind": session_kind,
        "practice_mode": practice_mode,
        "hardcore_mode": bool(payload.get("hardcore_mode", False)),
        "aids_used": bool(
            payload.get("aids_used", payload.get("practice_aids_used", False))
        ),
        "question_ids": question_ids,
        "answers": answers,
        "checked_answers": checked,
        "confidences": confidences,
        "error_types": error_types,
        "error_reasoning": error_reasoning,
        "marked_for_review": marked_for_review,
        "question_times": question_times,
        "current_idx": current_idx,
        "total_time_limit": max(60, int(payload.get("total_time_limit", 1800))),
        "started_at": started_at,
        "active_seconds": max(0.0, float(payload.get("active_seconds", 0.0))),
        "last_resumed_at": float(payload.get("last_resumed_at", payload.get("started_at", time.time()))),
        "paused": bool(payload.get("paused", False)),
        "learning_complete": bool(
            payload.get("learning_complete", session_kind != "daily")
        ),
        "learning_minutes": max(3, int(payload.get("learning_minutes", 8))),
        "competition_id": _normalize_competition_id(payload.get("competition_id")),
        "opec_number": _normalize_opec_number(payload.get("opec_number")),
    }


def active_elapsed_seconds(payload: dict, now: float | None = None) -> float:
    """Calcula tiempo activo sin contar el periodo en que la sesión estuvo pausada."""
    payload = normalize_daily_run(payload)
    if payload["paused"]:
        return payload["active_seconds"]
    current_time = time.time() if now is None else now
    return payload["active_seconds"] + max(
        0.0, current_time - payload["last_resumed_at"]
    )


def checkpoint_daily_run(payload: dict, now: float | None = None) -> dict:
    """Consolidate active time so a later offline gap is never counted."""
    now = time.time() if now is None else now
    normalized = normalize_daily_run(payload)
    _require_resumable(normalized)
    if not normalized["paused"]:
        normalized["active_seconds"] = active_elapsed_seconds(normalized, now)
        normalized["last_resumed_at"] = now
    return normalized


def pause_daily_run(payload: dict, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    normalized = normalize_daily_run(payload)
    _require_resumable(normalized)
    if not normalized["paused"]:
        normalized["active_seconds"] = active_elapsed_seconds(normalized, now)
        normalized["paused"] = True
    return normalized


def resume_daily_run(payload: dict, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    normalized = normalize_daily_run(payload)
    _require_resumable(normalized)
    normalized["last_resumed_at"] = now
    normalized["paused"] = False
    return normalized


def load_daily_run(
    db,
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> dict | None:
    competition_id, opec_number = _active_context(
        db, user_id, competition_id, opec_number
    )
    row = db.query(Configuration).filter_by(
        key_name=_key(user_id, competition_id, opec_number)
    ).first()
    if not row:
        return None
    try:
        payload = normalize_daily_run(json.loads(row.value))
        if not is_resumable_practice(
            payload["session_kind"], payload["practice_mode"]
        ):
            return None
        if competition_id is not None and payload["competition_id"] != competition_id:
            return None
        if opec_number is not None and payload["opec_number"] != opec_number:
            return None
        return payload if payload["question_ids"] else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def save_daily_run(
    db,
    user_id: int,
    payload: dict,
    competition_id: int | None = None,
    opec_number: str | None = None,
    expected_run_id: str | None = None,
) -> dict:
    initial_payload = normalize_daily_run(payload)
    _require_resumable(initial_payload)
    competition_id, opec_number = _active_context(
        db, user_id, competition_id, opec_number
    )
    if competition_id is None and opec_number is None:
        competition_id = _normalize_competition_id(payload.get("competition_id"))
        opec_number = _normalize_opec_number(payload.get("opec_number"))
    scoped_payload = dict(initial_payload)
    scoped_payload["competition_id"] = competition_id
    scoped_payload["opec_number"] = opec_number
    normalized = normalize_daily_run(scoped_payload)
    row_query = db.query(Configuration).filter_by(
        key_name=_key(user_id, competition_id, opec_number)
    )
    if expected_run_id:
        row_query = row_query.with_for_update()
    row = row_query.first()
    if row is None and expected_run_id:
        raise StudyRunConflictError(
            "La práctica guardada ya no existe o fue finalizada en otra pestaña."
        )
    if row is not None and expected_run_id:
        try:
            stored = normalize_daily_run(json.loads(row.value))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StudyRunConflictError(
                "La práctica guardada cambió y no se puede sobrescribir."
            ) from exc
        if stored["run_id"] != str(expected_run_id):
            raise StudyRunConflictError(
                "Otra pestaña guardó una práctica más reciente para esta OPEC."
            )
    if row is None:
        row = Configuration(
            key_name=_key(user_id, competition_id, opec_number), value="{}"
        )
        db.add(row)
    row.value = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)
    db.commit()
    return normalized


def clear_daily_run(
    db,
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
    expected_run_id: str | None = None,
) -> bool:
    competition_id, opec_number = _active_context(
        db, user_id, competition_id, opec_number
    )
    row_query = db.query(Configuration).filter_by(
        key_name=_key(user_id, competition_id, opec_number)
    )
    if expected_run_id:
        row_query = row_query.with_for_update()
    row = row_query.first()
    if row is None:
        return False
    try:
        stored = normalize_daily_run(json.loads(row.value))
    except (TypeError, ValueError, json.JSONDecodeError):
        if expected_run_id:
            return False
        stored = None
    if expected_run_id:
        if stored["run_id"] != str(expected_run_id):
            return False
    elif stored is not None and stored["session_kind"] != "daily":
        # Historical callers (notably the unchanged dashboard) invoke this
        # function without a run identifier to clean up the daily plan.  They
        # must never erase a resumable custom/training run by accident.
        return False
    db.delete(row)
    return True


def restore_daily_run_to_session(session_state, payload: dict) -> None:
    payload = normalize_daily_run(payload)
    _require_resumable(payload)
    session_state["exam_mode"] = True
    session_state["practice_run_id"] = payload["run_id"]
    session_state["exam_questions"] = list(payload["question_ids"])
    session_state["current_idx"] = payload["current_idx"]
    session_state["answers"] = dict(payload["answers"])
    session_state["checked_answers"] = dict(payload["checked_answers"])
    session_state["confidences"] = dict(payload.get("confidences", {}))
    session_state["error_types"] = dict(payload.get("error_types", {}))
    session_state["error_reasoning"] = dict(payload.get("error_reasoning", {}))
    session_state["marked_for_review"] = list(payload.get("marked_for_review", []))
    session_state["question_times"] = dict(payload.get("question_times", {}))
    session_state["hardcore_mode"] = payload["hardcore_mode"]
    session_state["study_session_kind"] = payload["session_kind"]
    session_state["practice_mode"] = payload["practice_mode"]
    session_state["practice_aids_used"] = payload["aids_used"]
    session_state["total_time_limit"] = payload["total_time_limit"]
    session_state["exam_start_time"] = payload["started_at"]
    session_state["active_seconds"] = payload.get("active_seconds", 0.0)
    session_state["last_resumed_at"] = payload.get("last_resumed_at", payload["started_at"])
    session_state["daily_run_paused"] = payload.get("paused", False)
    session_state["last_answer_time"] = time.time()
    session_state["tutor_explanation"] = None
    session_state["daily_learning_complete"] = payload["learning_complete"]
    session_state["daily_learning_minutes"] = payload["learning_minutes"]
    session_state["exam_scope"] = {
        "competition_id": payload.get("competition_id"),
        "opec_number": payload.get("opec_number"),
    }
