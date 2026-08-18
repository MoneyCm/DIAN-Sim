"""Canonical full-content fingerprints for portable question curation.

``hash_norm`` is intentionally retained because it is the historical stem
deduplication key.  It is not sufficient to reconcile two databases: a stem
can be shared while the case, options, key, rationale, scope or evidence
differs.  This module therefore hashes the complete question payload used by
the OPEC curation pilot.

Canonicalization rules
----------------------

* text is Unicode NFC, uses LF line endings and has outer whitespace removed;
* ``difficulty`` is serialized as an integer;
* ``options_json`` accepts a mapping or a JSON object string and is serialized
  with keys sorted recursively;
* the payload is UTF-8 JSON with sorted keys and compact separators;
* the digest is lowercase SHA-256 hexadecimal.

No case or question identifier is inferred here.  In particular, the explicit
``case_id`` remains part of the digest so that moving an item to another case
is treated as a material content change.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from typing import Any


QUESTION_FINGERPRINT_FIELDS = (
    "case_id",
    "track",
    "competency",
    "topic",
    "macro_dominio",
    "micro_competencia",
    "difficulty",
    "question_type",
    "stem",
    "options_json",
    "correct_key",
    "rationale",
    "source_refs",
    "hash_norm",
)


def _read(question: Mapping[str, Any] | object, field: str) -> Any:
    if isinstance(question, Mapping):
        return question.get(field)
    return getattr(question, field, None)


def _canonical_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return unicodedata.normalize("NFC", text)


def _canonical_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            _canonical_text(key): _canonical_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, str):
        return _canonical_text(value)
    return value


def canonical_options(value: Any) -> dict[str, Any]:
    """Return a canonical option mapping from a mapping or JSON object text."""

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("options_json no contiene JSON valido") from exc
    if not isinstance(value, Mapping):
        raise ValueError("options_json debe ser un objeto JSON")
    return _canonical_json_value(value)


def canonical_question_payload(
    question: Mapping[str, Any] | object,
) -> dict[str, Any]:
    """Build the exact canonical payload covered by the content digest."""

    difficulty = _read(question, "difficulty")
    if difficulty is None or isinstance(difficulty, bool):
        raise ValueError("difficulty debe ser un entero")
    try:
        difficulty = int(difficulty)
    except (TypeError, ValueError) as exc:
        raise ValueError("difficulty debe ser un entero") from exc

    payload = {
        field: _canonical_text(_read(question, field))
        for field in QUESTION_FINGERPRINT_FIELDS
        if field not in {"difficulty", "options_json"}
    }
    payload["difficulty"] = difficulty
    payload["options_json"] = canonical_options(_read(question, "options_json"))
    return payload


def canonical_question_json(question: Mapping[str, Any] | object) -> str:
    """Serialize a question with stable Unicode JSON rules."""

    return json.dumps(
        canonical_question_payload(question),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_question_content_fingerprint(
    question: Mapping[str, Any] | object,
) -> str:
    """Return the full-content SHA-256 fingerprint for a question."""

    canonical = canonical_question_json(question).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
