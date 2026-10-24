"""DEMO-ONLY endpoints. Registered only when DEMO_MODE=1. Keep the server on localhost / a private network."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from ..config import current_config
from ..connectors.synthetic import SyntheticConnector
from ..db import get_db
from ..errors import ApiError
from ..models import FaultMode
from ..request_utils import json_body, require_actor
from ..services import seed
from ..services.audit_service import log_event

bp = Blueprint("dev", __name__)


def _synthetic() -> SyntheticConnector:
    connector = current_app.extensions["connector"]
    if not isinstance(connector, SyntheticConnector):
        raise ApiError("NOT_SUPPORTED", "This dev endpoint only works with the synthetic connector", 409)
    return connector


@bp.post("/reset")
def reset():
    """Wipe the DB (including the audit log), reseed HR + exclusions, reset the synthetic SaaS state."""
    actor = require_actor()
    db = get_db()
    counts = seed.reset_and_seed(db, current_app.extensions["hr_source"], current_config())
    connector = current_app.extensions["connector"]
    connector_reset = isinstance(connector, SyntheticConnector)
    if connector_reset:
        connector.reset()
    result = {**counts, "connector": connector.name, "connector_reset": connector_reset,
              "connector_accounts": len(connector.list_accounts())}
    log_event(db, actor, "DEMO_RESET", "system", "demo", result)
    db.commit()
    return jsonify({"data": {"reset": True, **result}})


@bp.get("/connector/accounts")
def connector_accounts():
    """Ground truth straight from the connector (not from our DB). Handy for checking real outcomes."""
    accounts = _synthetic().list_accounts()
    return jsonify({"data": [a.to_dict() for a in accounts]})


@bp.get("/fault-injection")
def get_fault_injection():
    return jsonify({"data": _synthetic().describe_faults()})


@bp.post("/fault-injection")
def set_fault_injection():
    actor = require_actor()
    connector = _synthetic()
    body = json_body()
    try:
        mode = FaultMode(body.get("mode"))
    except ValueError:
        allowed = [m.value for m in FaultMode]
        raise ApiError("VALIDATION_ERROR", f"mode must be one of {allowed}", 422)
    system, account_id = body.get("system"), body.get("external_account_id")
    if (system is None) != (account_id is None):
        raise ApiError("VALIDATION_ERROR", "Provide both system and external_account_id, or neither", 422)
    if system is not None and connector.get_account(system, account_id) is None:
        raise ApiError("NOT_FOUND", f"Account {system}/{account_id} not found", 404)
    connector.set_fault(mode, system, account_id)
    db = get_db()
    log_event(db, actor, "FAULT_INJECTION_SET", "system", "demo",
              {"mode": mode.value, "system": system, "external_account_id": account_id})
    db.commit()
    return jsonify({"data": connector.describe_faults()})


@bp.delete("/fault-injection")
def clear_fault_injection():
    actor = require_actor()
    connector = _synthetic()
    connector.clear_faults()
    db = get_db()
    log_event(db, actor, "FAULT_INJECTION_CLEARED", "system", "demo")
    db.commit()
    return jsonify({"data": connector.describe_faults()})
