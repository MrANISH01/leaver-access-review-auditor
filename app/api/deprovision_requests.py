from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..config import current_config
from ..db import get_db
from ..errors import ApiError
from ..models import RequestStatus
from ..repositories import findings as findings_repo
from ..repositories import requests as requests_repo
from ..request_utils import optional_note, require_actor
from ..services import request_service

bp = Blueprint("deprovision_requests", __name__)


def _present(db, req: dict, detail: bool = False) -> dict:
    out = dict(req)
    # `verified` is derived from status and only the (Stage 4) verifier can ever move a request to VERIFIED.
    out["verified"] = req["status"] == RequestStatus.VERIFIED.value
    finding = findings_repo.get_finding(db, req["finding_id"])
    out["finding"] = {k: finding[k] for k in ("id", "scan_id", "classification", "match_method",
                                              "match_confidence", "reason", "employee", "account")} if finding else None
    if detail:
        out["executions"] = requests_repo.list_executions(db, req["id"])        # empty until Stage 4
        out["verifications"] = requests_repo.list_verifications(db, req["id"])  # empty until Stage 4
    return out


@bp.post("/findings/<int:finding_id>/deprovision-requests")
def prepare(finding_id: int):
    """Prepare (not execute) a disable request. Does not touch the SaaS account."""
    actor = require_actor()
    db = get_db()
    req = request_service.prepare_request(db, actor, finding_id)
    return jsonify({"data": _present(db, req, detail=True)}), 201


@bp.get("/deprovision-requests")
def list_requests():
    status = request.args.get("status")
    if status and status not in {s.value for s in RequestStatus}:
        raise ApiError("VALIDATION_ERROR", f"status must be one of {[s.value for s in RequestStatus]}", 422)
    db = get_db()
    return jsonify({"data": [_present(db, r) for r in requests_repo.list_requests(db, status)]})


@bp.get("/deprovision-requests/<int:request_id>")
def get_request(request_id: int):
    db = get_db()
    req = requests_repo.get(db, request_id)
    if req is None:
        raise ApiError("NOT_FOUND", f"Deprovision request {request_id} not found", 404)
    return jsonify({"data": _present(db, req, detail=True)})


def _decide(request_id: int, decision: str):
    actor = require_actor()
    note = optional_note()
    db = get_db()
    req, replayed = request_service.decide_request(db, current_config(), actor, request_id, decision, note)
    return jsonify({"data": _present(db, req, detail=True), "meta": {"idempotent_replay": replayed}})


@bp.post("/deprovision-requests/<int:request_id>/approve")
def approve(request_id: int):
    return _decide(request_id, request_service.APPROVE)


@bp.post("/deprovision-requests/<int:request_id>/reject")
def reject(request_id: int):
    return _decide(request_id, request_service.REJECT)


@bp.post("/deprovision-requests/<int:request_id>/execute")
def execute(request_id: int):
    actor = require_actor()
    db = get_db()
    req, replayed = request_service.execute_request(
        db, current_config(), current_app.extensions["connector"],
        current_app.extensions["hr_source"], actor, request_id
    )
    return jsonify({"data": _present(db, req, detail=True), "meta": {"idempotent_replay": replayed}})

