from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..errors import ApiError
from ..models import Classification
from ..repositories import findings as findings_repo
from ..repositories import scans as scans_repo
from ..services.classification import is_deprovision_eligible

bp = Blueprint("findings", __name__)


def _present(finding: dict) -> dict:
    # UI hint only. The server re-checks eligibility itself when a request is prepared (Stage 3).
    finding["deprovision_eligible"] = is_deprovision_eligible(finding["classification"], finding["match_confidence"])
    return finding


@bp.get("/findings")
def list_findings():
    db = get_db()
    raw_scan_id = request.args.get("scan_id")
    if raw_scan_id is None:
        scan = scans_repo.latest_completed(db)
    else:
        try:
            scan = scans_repo.get(db, int(raw_scan_id))
        except ValueError:
            raise ApiError("VALIDATION_ERROR", "scan_id must be an integer", 422)
        if scan is None:
            raise ApiError("NOT_FOUND", f"Scan {raw_scan_id} not found", 404)

    classification = request.args.get("classification")
    if classification and classification not in {c.value for c in Classification}:
        raise ApiError("VALIDATION_ERROR",
                       f"classification must be one of {[c.value for c in Classification]}", 422)

    if scan is None:   # no scan has been run yet
        return jsonify({"data": [], "meta": {"scan_id": None, "count": 0}})
    items = findings_repo.list_findings(db, scan["id"], classification, request.args.get("system"))
    return jsonify({"data": [_present(f) for f in items], "meta": {"scan_id": scan["id"], "count": len(items)}})


@bp.get("/findings/<int:finding_id>")
def get_finding(finding_id: int):
    finding = findings_repo.get_finding(get_db(), finding_id)
    if finding is None:
        raise ApiError("NOT_FOUND", f"Finding {finding_id} not found", 404)
    return jsonify({"data": _present(finding)})
