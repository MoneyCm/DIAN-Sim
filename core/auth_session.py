"""Signed, password-free payloads used to restore a browser session."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def create_session_token(user_id: int, username: str, role: str, secret: str, ttl_seconds: int) -> str:
    if not secret:
        raise ValueError("A signing secret is required")
    payload = {
        "uid": int(user_id),
        "username": str(username),
        "role": str(role),
        "exp": int(time.time()) + int(ttl_seconds),
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def verify_session_token(token: str, secret: str, now: int | None = None) -> dict | None:
    if not token or not secret or "." not in token:
        return None
    try:
        encoded, supplied_signature = token.rsplit(".", 1)
        expected_signature = hmac.new(
            secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding).decode("utf-8"))
        if int(payload.get("exp", 0)) <= int(time.time() if now is None else now):
            return None
        if not payload.get("uid") or not payload.get("username"):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
