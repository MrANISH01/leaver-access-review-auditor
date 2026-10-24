from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..errors import ApiError
from ..repositories import audit as audit_repo

bp = Blueprint("audit", __name__)


@bp.get("/audit-log")
def audit_log():
    """Read-only view of the append-only audit trail (most recent `limit` events, oldest first)."""
    try:
        limit = int(request.args.get("limit", 200))
    except ValueError:
        raise ApiError("VALIDATION_ERROR", "limit must be an integer between 1 and 500", 422)
    if not 1 <= limit <= 500:
        raise ApiError("VALIDATION_ERROR", "limit must be an integer between 1 and 500", 422)
    events = audit_repo.list_events(get_db(), request.args.get("entity_type"), request.args.get("entity_id"),
                                    request.args.get("event"), limit)
    return jsonify({"data": events, "meta": {"count": len(events)}})
