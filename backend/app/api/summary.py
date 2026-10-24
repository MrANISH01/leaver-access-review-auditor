from __future__ import annotations

from flask import Blueprint, jsonify

from ..db import get_db
from ..models import Classification
from ..repositories import findings as findings_repo
from ..repositories import scans as scans_repo

bp = Blueprint("summary", __name__)


def _request_count(db, status: str) -> int:
    return db.execute("SELECT COUNT(*) FROM deprovision_requests WHERE status = ?", (status,)).fetchone()[0]


@bp.get("/summary")
def summary():
    db = get_db()
    scan = scans_repo.latest_completed(db)
    counts = findings_repo.counts_by_classification(db, scan["id"]) if scan else {c.value: 0 for c in Classification}
    return jsonify({"data": {
        "latest_scan": {"id": scan["id"], "finished_at": scan["finished_at"]} if scan else None,
        "findings_by_classification": counts,
        "total_findings": sum(counts.values()),
        "leavers_active": counts["LEAVER_ACTIVE"],
        "excluded": counts["EXCLUDED"],
        "needs_review": counts["NEEDS_REVIEW"],
        "pending_approval": _request_count(db, "PREPARED"),   # always 0 until Stage 3
        "verified": _request_count(db, "VERIFIED"),           # always 0 until Stage 4
    }})
