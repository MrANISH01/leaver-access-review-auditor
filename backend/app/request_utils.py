from __future__ import annotations

from flask import request

from .config import ACTOR_RE
from .errors import ApiError


def require_actor() -> str:
    """Return the X-Actor header value.

    DEMO-ONLY IDENTITY. This is an unauthenticated label used for audit attribution; any client
    that can reach the API can claim any actor. It is NOT authentication. Approval and execution
    are enforced by server-side state in the database, never by anything the client asserts.
    """
    actor = request.headers.get("X-Actor", "").strip()
    if not actor:
        raise ApiError("ACTOR_REQUIRED", "X-Actor header is required (demo-only identity, not authentication)", 400)
    if not ACTOR_RE.match(actor):
        raise ApiError("INVALID_ACTOR", "X-Actor may contain letters, digits and . _ @ + - only (max 100 chars)", 400)
    return actor


def json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("INVALID_JSON", "Request body must be a JSON object", 400)
    return data


def optional_note(max_len: int = 500) -> str | None:
    """Optional {"note": "..."} body. An empty body is fine; a non-object or non-string note is a 422."""
    if not request.get_data():
        return None
    body = json_body()
    note = body.get("note")
    if note is None:
        return None
    if not isinstance(note, str) or len(note.strip()) > max_len:
        raise ApiError("VALIDATION_ERROR", f"note must be a string of at most {max_len} characters", 422)
    return note.strip() or None
