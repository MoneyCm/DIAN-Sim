"""Persistencia ligera del último resultado por usuario."""
import json
import re
from datetime import datetime, timezone
from db.models import Configuration, UserOPEC


def _normalize_opec_number(value: object) -> str | None:
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


def _scoped_key(
    prefix: str,
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> str:
    base = f"{prefix}:{int(user_id)}"
    competition_id = _normalize_competition_id(competition_id)
    opec_number = _normalize_opec_number(opec_number)
    if competition_id is None and opec_number is None:
        return base
    return f"{base}:competition:{competition_id or 'none'}:opec:{opec_number or 'none'}"


def _key(
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> str:
    return _scoped_key("last_result", user_id, competition_id, opec_number)


def _history_key(
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> str:
    return _scoped_key("result_history", user_id, competition_id, opec_number)


def save_last_result(
    db,
    user_id: int,
    result: dict,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> None:
    competition_id, opec_number = _active_context(
        db, user_id, competition_id, opec_number
    )
    if competition_id is None and opec_number is None:
        competition_id = _normalize_competition_id(result.get("competition_id"))
        opec_number = _normalize_opec_number(result.get("opec_number"))
    stored_result = dict(result)
    stored_result["competition_id"] = competition_id
    stored_result["opec_number"] = opec_number
    stored_result.setdefault("saved_at", datetime.now(timezone.utc).isoformat())
    row = db.query(Configuration).filter_by(
        key_name=_key(user_id, competition_id, opec_number)
    ).first()
    if row is None:
        row = Configuration(
            key_name=_key(user_id, competition_id, opec_number), value="{}"
        )
        db.add(row)
    row.value = json.dumps(stored_result, ensure_ascii=False, separators=(",", ":"), default=str)

    history_row = db.query(Configuration).filter_by(
        key_name=_history_key(user_id, competition_id, opec_number)
    ).first()
    if history_row is None:
        history_row = Configuration(
            key_name=_history_key(user_id, competition_id, opec_number), value="[]"
        )
        db.add(history_row)
        history = []
    else:
        try:
            history = json.loads(history_row.value)
            if not isinstance(history, list):
                history = []
        except (TypeError, ValueError, json.JSONDecodeError):
            history = []
    history.append(stored_result)
    history_row.value = json.dumps(history[-100:], ensure_ascii=False, separators=(",", ":"), default=str)


def load_last_result(
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
        value = json.loads(row.value)
        if not isinstance(value, dict) or not value:
            return None
        if competition_id is not None and _normalize_competition_id(
            value.get("competition_id")
        ) != competition_id:
            return None
        if opec_number is not None and _normalize_opec_number(
            value.get("opec_number")
        ) != opec_number:
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def load_result_history(
    db,
    user_id: int,
    competition_id: int | None = None,
    opec_number: str | None = None,
) -> list[dict]:
    competition_id, opec_number = _active_context(
        db, user_id, competition_id, opec_number
    )
    row = db.query(Configuration).filter_by(
        key_name=_history_key(user_id, competition_id, opec_number)
    ).first()
    if not row:
        return []
    try:
        value = json.loads(row.value)
        if not isinstance(value, list):
            return []
        return [
            item for item in value
            if isinstance(item, dict)
            and (
                competition_id is None
                or _normalize_competition_id(item.get("competition_id")) == competition_id
            )
            and (
                opec_number is None
                or _normalize_opec_number(item.get("opec_number")) == opec_number
            )
        ]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
