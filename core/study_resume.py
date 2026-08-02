"""Persistence helpers for resuming an interrupted daily study session."""

from __future__ import annotations

import json
import time

from db.models import Configuration


def _key(user_id: int) -> str:
    return f"active_daily_run:{int(user_id)}"


def normalize_daily_run(payload: dict) -> dict:
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
    current_idx = max(0, min(int(payload.get("current_idx", 0)), max(len(question_ids) - 1, 0)))
    return {
        "question_ids": question_ids,
        "answers": answers,
        "checked_answers": checked,
        "confidences": confidences,
        "error_types": error_types,
        "current_idx": current_idx,
        "total_time_limit": max(60, int(payload.get("total_time_limit", 1800))),
        "started_at": float(payload.get("started_at", time.time())),
        "active_seconds": max(0.0, float(payload.get("active_seconds", 0.0))),
        "last_resumed_at": float(payload.get("last_resumed_at", payload.get("started_at", time.time()))),
        "paused": bool(payload.get("paused", False)),
        "learning_complete": bool(payload.get("learning_complete", False)),
        "learning_minutes": max(3, int(payload.get("learning_minutes", 8))),
    }


def active_elapsed_seconds(payload: dict, now: float | None = None) -> float:
    """Calcula tiempo activo sin contar el periodo en que la sesión estuvo pausada."""
    payload = normalize_daily_run(payload)
    if payload["paused"]:
        return payload["active_seconds"]
    return payload["active_seconds"] + max(0.0, (now or time.time()) - payload["last_resumed_at"])


def pause_daily_run(payload: dict, now: float | None = None) -> dict:
    now = now or time.time()
    normalized = normalize_daily_run(payload)
    if not normalized["paused"]:
        normalized["active_seconds"] = active_elapsed_seconds(normalized, now)
        normalized["paused"] = True
    return normalized


def resume_daily_run(payload: dict, now: float | None = None) -> dict:
    now = now or time.time()
    normalized = normalize_daily_run(payload)
    normalized["last_resumed_at"] = now
    normalized["paused"] = False
    return normalized


def load_daily_run(db, user_id: int) -> dict | None:
    row = db.query(Configuration).filter_by(key_name=_key(user_id)).first()
    if not row:
        return None
    try:
        payload = normalize_daily_run(json.loads(row.value))
        return payload if payload["question_ids"] else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def save_daily_run(db, user_id: int, payload: dict) -> dict:
    normalized = normalize_daily_run(payload)
    row = db.query(Configuration).filter_by(key_name=_key(user_id)).first()
    if row is None:
        row = Configuration(key_name=_key(user_id), value="{}")
        db.add(row)
    row.value = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)
    db.commit()
    return normalized


def clear_daily_run(db, user_id: int) -> None:
    row = db.query(Configuration).filter_by(key_name=_key(user_id)).first()
    if row:
        db.delete(row)


def restore_daily_run_to_session(session_state, payload: dict) -> None:
    session_state["exam_mode"] = True
    session_state["exam_questions"] = list(payload["question_ids"])
    session_state["current_idx"] = payload["current_idx"]
    session_state["answers"] = dict(payload["answers"])
    session_state["checked_answers"] = dict(payload["checked_answers"])
    session_state["confidences"] = dict(payload.get("confidences", {}))
    session_state["error_types"] = dict(payload.get("error_types", {}))
    session_state["hardcore_mode"] = False
    session_state["study_session_kind"] = "daily"
    session_state["total_time_limit"] = payload["total_time_limit"]
    session_state["exam_start_time"] = payload["started_at"]
    session_state["active_seconds"] = payload.get("active_seconds", 0.0)
    session_state["last_resumed_at"] = payload.get("last_resumed_at", payload["started_at"])
    session_state["daily_run_paused"] = payload.get("paused", False)
    session_state["last_answer_time"] = time.time()
    session_state["tutor_explanation"] = None
    session_state["daily_learning_complete"] = payload["learning_complete"]
    session_state["daily_learning_minutes"] = payload["learning_minutes"]
