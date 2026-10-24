from __future__ import annotations

from flask import Blueprint, jsonify

from ..config import current_config
from ..request_utils import require_actor

bp = Blueprint("session", __name__)


@bp.get("/whoami")
def whoami():
    """UI hint: may this X-Actor approve/reject at all? The server re-checks on every decision, and
    separation of duties (approver != preparer) is still evaluated per request."""
    actor = require_actor()
    return jsonify({"data": {"actor": actor, "can_approve": current_config().is_approver(actor)}})
