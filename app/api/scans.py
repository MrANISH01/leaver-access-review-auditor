from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from ..db import get_db
from ..errors import ApiError
from ..repositories import scans as scans_repo
from ..request_utils import require_actor
from ..services import scan_service

bp = Blueprint("scans", __name__)


@bp.post("/scans")
def create_scan():
    """Run a read-only leaver scan now. Never modifies any SaaS account."""
    actor = require_actor()
    try:
        scan = scan_service.run_scan(get_db(), current_app.extensions["connector"],
                                     current_app.extensions["hr_source"], actor)
    except scan_service.ScanFailed as exc:
        raise ApiError("SOURCE_UNAVAILABLE",
                       f"Scan {exc.scan_id} failed because a source system could not be read", 502)
    return jsonify({"data": scan}), 201


@bp.get("/scans")
def list_scans():
    return jsonify({"data": scans_repo.list_all(get_db())})


@bp.get("/scans/<int:scan_id>")
def get_scan(scan_id: int):
    scan = scans_repo.get(get_db(), scan_id)
    if scan is None:
        raise ApiError("NOT_FOUND", f"Scan {scan_id} not found", 404)
    return jsonify({"data": scan})
