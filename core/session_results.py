"""Persistencia ligera del último resultado por usuario."""
import json
from datetime import datetime, timezone
from db.models import Configuration


def _key(user_id: int) -> str:
    return f"last_result:{int(user_id)}"


def _history_key(user_id: int) -> str:
    return f"result_history:{int(user_id)}"


def save_last_result(db, user_id: int, result: dict) -> None:
    stored_result = dict(result)
    stored_result.setdefault("saved_at", datetime.now(timezone.utc).isoformat())
    row = db.query(Configuration).filter_by(key_name=_key(user_id)).first()
    if row is None:
        row = Configuration(key_name=_key(user_id), value="{}")
        db.add(row)
    row.value = json.dumps(stored_result, ensure_ascii=False, separators=(",", ":"), default=str)

    history_row = db.query(Configuration).filter_by(key_name=_history_key(user_id)).first()
    if history_row is None:
        history_row = Configuration(key_name=_history_key(user_id), value="[]")
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


def load_last_result(db, user_id: int) -> dict | None:
    row = db.query(Configuration).filter_by(key_name=_key(user_id)).first()
    if not row:
        return None
    try:
        value = json.loads(row.value)
        return value if isinstance(value, dict) and value else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def load_result_history(db, user_id: int) -> list[dict]:
    row = db.query(Configuration).filter_by(key_name=_history_key(user_id)).first()
    if not row:
        return []
    try:
        value = json.loads(row.value)
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
