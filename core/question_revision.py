"""Canonical hashing for immutable question revisions."""

from __future__ import annotations

import hashlib
import json


def question_revision_hash(question, difficulty: int) -> str:
    """Hash every mutable field that defines the delivered question version."""
    payload = {
        "stem": str(getattr(question, "stem", "") or "").strip(),
        "options": getattr(question, "options_json", None) or {},
        "correct_key": getattr(question, "correct_key", None),
        "rationale": str(getattr(question, "rationale", "") or "").strip(),
        "difficulty": int(difficulty),
        "question_type": str(
            getattr(question, "question_type", "SITUATIONAL") or "SITUATIONAL"
        ).upper(),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
