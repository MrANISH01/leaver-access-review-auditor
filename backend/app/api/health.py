from __future__ import annotations

import sqlite3

from flask import Blueprint, current_app, jsonify

from .. import __version__
from ..config import current_config
from ..db import get_db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
        db_status = "ok"
    except sqlite3.Error:
        db_status = "error"
    cfg = current_config()
    body = {"data": {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": __version__,
        "connector": current_app.extensions["connector"].name,
        "hr_source": current_app.extensions["hr_source"].name,
        "demo_mode": cfg.demo_mode,
        "approvers_configured": len(cfg.approver_actors) > 0,
        "database": db_status,
    }}
    return jsonify(body), (200 if db_status == "ok" else 503)
