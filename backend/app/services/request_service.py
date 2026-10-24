"""Deprovisioning request workflow, Stage 3: prepare, approve, reject.

Safety properties (all enforced HERE, server-side; the frontend is never trusted):
  * Only a finding that is LEAVER_ACTIVE with HIGH confidence on an INDIVIDUAL account, not excluded,
    and from the latest completed scan, may have a request prepared.
  * Preparing, approving or rejecting NEVER touches a connector. Nothing here can disable an account.
  * Approving/rejecting requires membership of the APPROVER_ACTORS allowlist (fail closed when empty).
  * The approver must differ from the preparer (case-insensitive). A DB trigger backs this up.
  * Decisions are atomic compare-and-set transitions, so repeats and races are safe. Repeating the SAME
    decision by the SAME actor is an idempotent replay (no second transition, no second approval event).
  * Every attempt, successful or refused, lands in the append-only audit log before the error is raised.
"""
from __future__ import annotations

import sqlite3
import uuid

from ..config import Config
from ..connectors.base import ConnectorError, HRSource, SaaSConnector
from ..errors import ApiError
from ..models import AccountStatus, AccountType, EmploymentStatus, RequestStatus, can_transition
from ..repositories import exclusions as exclusions_repo
from ..repositories import findings as findings_repo
from ..repositories import requests as requests_repo
from ..repositories import scans as scans_repo
from ..utils import utcnow_iso
from .audit_service import log_event
from .classification import is_deprovision_eligible

APPROVE, REJECT = "APPROVE", "REJECT"
_TARGET = {APPROVE: RequestStatus.APPROVED, REJECT: RequestStatus.REJECTED}
_PAST = {APPROVE: "APPROVED", REJECT: "REJECTED"}


def _deny(db: sqlite3.Connection, actor: str, event: str, entity_type: str, entity_id, code: str, message: str,
          status: int, reason: str, details: dict | None = None):
    """Record the refused attempt (committed on its own), then raise the API error."""
    db.rollback()   # discard anything half-done; the audit row must stand alone
    log_event(db, actor, event, entity_type, str(entity_id),
              {"reason": reason, "code": code, **(details or {})})
    db.commit()
    raise ApiError(code, message, status, details=details)


# ------------------------------------------------------------------ prepare
def prepare_request(db: sqlite3.Connection, actor: str, finding_id: int) -> dict:
    def deny(code, message, status, reason, details=None):
        _deny(db, actor, "DEPROVISION_PREPARE_DENIED", "finding", finding_id, code, message, status, reason, details)

    finding = findings_repo.get_finding(db, finding_id)
    if finding is None:
        deny("NOT_FOUND", f"Finding {finding_id} not found", 404, "NOT_FOUND")

    account = finding["account"]
    if not is_deprovision_eligible(finding["classification"], finding["match_confidence"]):
        deny("NOT_ELIGIBLE",
             f"Finding is {finding['classification']} (match confidence {finding['match_confidence']}); only "
             "HIGH-confidence LEAVER_ACTIVE findings can have a deprovisioning request prepared",
             422, "NOT_ELIGIBLE", {"classification": finding["classification"],
                                    "match_confidence": finding["match_confidence"]})
    if account["account_type"] != AccountType.INDIVIDUAL.value:   # defence in depth: never shared/service
        deny("NOT_ELIGIBLE", f"{account['account_type']} accounts are never deprovisioned as individual leavers",
             422, "NOT_INDIVIDUAL_ACCOUNT", {"account_type": account["account_type"]})
    if (account["system"], account["external_account_id"]) in exclusions_repo.load_map(db):
        deny("NOT_ELIGIBLE", "This account is now explicitly excluded", 422, "EXPLICITLY_EXCLUDED")

    latest = scans_repo.latest_completed(db)
    if latest is None or finding["scan_id"] != latest["id"]:
        deny("STALE_FINDING", "This finding is from an older scan. Run a new scan and prepare from its findings",
             409, "STALE_FINDING", {"finding_scan_id": finding["scan_id"], "latest_scan_id": latest["id"] if latest else None})

    def duplicate(existing: dict):
        deny("DUPLICATE_REQUEST",
             f"An open request ({existing['status']}) already exists for this account: #{existing['id']}",
             409, "DUPLICATE_REQUEST", {"existing_request_id": existing["id"], "existing_status": existing["status"]})

    existing = requests_repo.find_open_for_account(db, account["system"], account["external_account_id"])
    if existing:
        duplicate(existing)

    try:
        request_id = requests_repo.insert(
            db, finding_id, account["system"], account["external_account_id"],
            f"deprov-{finding_id}-{uuid.uuid4().hex}", actor, utcnow_iso())
        log_event(db, actor, "DEPROVISION_PREPARED", "deprovision_request", request_id,
                  {"finding_id": finding_id, "system": account["system"],
                   "external_account_id": account["external_account_id"], "action": "DISABLE",
                   "employee_id": finding["employee"]["employee_id"] if finding["employee"] else None})
        db.commit()
    except sqlite3.IntegrityError:   # lost a race against another prepare: the unique indexes held the line
        db.rollback()
        duplicate(requests_repo.find_open_for_account(db, account["system"], account["external_account_id"])
                  or {"id": None, "status": "UNKNOWN"})
    return requests_repo.get(db, request_id)


# ------------------------------------------------------------------ approve / reject
def decide_request(db: sqlite3.Connection, config: Config, actor: str, request_id: int, decision: str,
                   note: str | None) -> tuple[dict, bool]:
    """Approve or reject. Returns (request, idempotent_replay)."""
    assert decision in _TARGET
    target = _TARGET[decision]
    denied_event = f"DEPROVISION_{decision}_DENIED"

    def deny(code, message, status, reason, details=None):
        _deny(db, actor, denied_event, "deprovision_request", request_id, code, message, status, reason, details)

    # 1. Authorization first, before revealing anything about the request.
    if not config.is_approver(actor):
        reason = "NO_APPROVERS_CONFIGURED" if not config.approver_actors else "UNAUTHORIZED_APPROVER"
        deny("APPROVER_NOT_AUTHORIZED",
             "This actor is not on the approver allowlist" if config.approver_actors
             else "No approvers are configured on the server, so nothing can be approved or rejected",
             403, reason)

    # 2. Lookup.
    req = requests_repo.get(db, request_id)
    if req is None:
        deny("NOT_FOUND", f"Deprovision request {request_id} not found", 404, "NOT_FOUND")

    # 3. Separation of duties (approval only; a preparer may withdraw their own request by rejecting it).
    if decision == APPROVE and actor.lower() == req["prepared_by"].lower():
        deny("SELF_APPROVAL_FORBIDDEN", "The person who prepared a request cannot approve it", 403,
             "SELF_APPROVAL", {"prepared_by": req["prepared_by"]})

    # 4. Idempotent replay: same actor repeating the decision that is already recorded.
    def replay(current: dict) -> tuple[dict, bool]:
        log_event(db, actor, "DEPROVISION_DECISION_REPLAYED", "deprovision_request", request_id,
                  {"decision": _PAST[decision], "status": current["status"]})
        db.commit()
        return current, True

    if (req["status"] == target.value and (req["decided_by"] or "").lower() == actor.lower()):
        return replay(req)

    # 5. State machine.
    if not can_transition(req["status"], target.value):
        deny("INVALID_STATE", f"Cannot {decision.lower()} a request that is {req['status']}", 409,
             "INVALID_STATE", {"current_status": req["status"], "attempted": target.value})

    # 6. Atomic compare-and-set + audit row in ONE transaction.
    try:
        won = requests_repo.decide(db, request_id, RequestStatus.PREPARED.value, target.value,
                                   actor, utcnow_iso(), note)
        if won:
            log_event(db, actor, f"DEPROVISION_{_PAST[decision]}", "deprovision_request", request_id,
                      {"from": "PREPARED", "to": target.value, "note": note, "prepared_by": req["prepared_by"],
                       "system": req["system"], "external_account_id": req["external_account_id"]})
            db.commit()
            return requests_repo.get(db, request_id), False
    except sqlite3.DatabaseError as exc:   # the DB-level separation-of-duties trigger fired
        db.rollback()
        deny("SELF_APPROVAL_FORBIDDEN" if "separation of duties" in str(exc) else "INVALID_STATE",
             "Refused by a database integrity rule", 403 if "separation" in str(exc) else 409, "DB_RULE")

    # Lost a race: someone else moved the request between our read and our update.
    db.rollback()
    current = requests_repo.get(db, request_id)
    if current["status"] == target.value and (current["decided_by"] or "").lower() == actor.lower():
        return replay(current)
    deny("INVALID_STATE", f"Cannot {decision.lower()} a request that is {current['status']}", 409,
         "INVALID_STATE", {"current_status": current["status"], "attempted": target.value})


# ------------------------------------------------------------------ execute
def execute_request(db: sqlite3.Connection, config: Config, connector: SaaSConnector,
                    hr_source: HRSource, actor: str, request_id: int) -> tuple[dict, bool]:
    """Execute an approved deprovisioning request with prechecks and independent verification.

    Returns (request, idempotent_replay).
    """
    def deny(code: str, message: str, status: int, reason: str, details: dict | None = None):
        _deny(db, actor, "DEPROVISION_EXECUTE_DENIED", "deprovision_request", request_id,
              code, message, status, reason, details)

    # 1. Lookup
    req = requests_repo.get(db, request_id)
    if req is None:
        deny("NOT_FOUND", f"Deprovision request {request_id} not found", 404, "NOT_FOUND")

    # 2. Idempotent replay: if already VERIFIED
    if req["status"] == RequestStatus.VERIFIED.value:
        log_event(db, actor, "DEPROVISION_EXECUTION_REPLAYED", "deprovision_request", request_id,
                  {"status": req["status"]})
        db.commit()
        return req, True

    # 3. Only APPROVED requests can be executed
    if req["status"] != RequestStatus.APPROVED.value:
        deny("INVALID_STATE",
             f"Cannot execute a request that is {req['status']}; only APPROVED requests can be executed",
             409, "INVALID_STATE",
             {"current_status": req["status"], "required_status": RequestStatus.APPROVED.value})

    # 4. Mandatory pre-execution live rechecks immediately before execution
    # 4a. Live HR employment status recheck
    finding = findings_repo.get_finding(db, req["finding_id"])
    employee_id = finding["employee"]["employee_id"] if finding and finding.get("employee") else None
    if employee_id:
        try:
            employee = hr_source.get_employee(employee_id)
        except Exception as exc:
            deny("SOURCE_UNAVAILABLE", f"Failed to check live HR record for employee {employee_id}: {exc}",
                 502, "HR_SOURCE_ERROR")
        if employee is None:
            deny("STALE_STATE", f"Pre-execution check failed: employee {employee_id} not found in HR source",
                 409, "HR_EMPLOYEE_NOT_FOUND", {"employee_id": employee_id})
        if employee.employment_status != EmploymentStatus.TERMINATED:
            deny("STALE_STATE",
                 f"Pre-execution check failed: employee {employee_id} is {employee.employment_status.value}, "
                 "not TERMINATED (status changed or employee rehired)",
                 409, "EMPLOYEE_NOT_TERMINATED",
                 {"employee_id": employee_id, "current_employment_status": employee.employment_status.value})

    # 4b. Live SaaS account status recheck
    try:
        live_account = connector.get_account(req["system"], req["external_account_id"])
    except Exception as exc:
        deny("SOURCE_UNAVAILABLE",
             f"Failed to check live SaaS account {req['external_account_id']} in {req['system']}: {exc}",
             502, "CONNECTOR_SOURCE_ERROR")
    if live_account is None:
        deny("STALE_STATE",
             f"Pre-execution check failed: account {req['external_account_id']} not found in {req['system']}",
             409, "ACCOUNT_NOT_FOUND",
             {"system": req["system"], "external_account_id": req["external_account_id"]})
    if live_account.status != AccountStatus.ACTIVE:
        deny("STALE_STATE",
             f"Pre-execution check failed: account {req['external_account_id']} in {req['system']} "
             f"is {live_account.status.value}, not ACTIVE",
             409, "ACCOUNT_NOT_ACTIVE",
             {"system": req["system"], "external_account_id": req["external_account_id"],
              "current_status": live_account.status.value})

    # 5. Atomic state transition: APPROVED -> EXECUTING
    exec_ts = utcnow_iso()
    won = requests_repo.transition_status(
        db, request_id, RequestStatus.APPROVED.value, RequestStatus.EXECUTING.value,
        executed_at=exec_ts)
    if not won:
        db.rollback()
        current = requests_repo.get(db, request_id)
        if current and current["status"] == RequestStatus.VERIFIED.value:
            log_event(db, actor, "DEPROVISION_EXECUTION_REPLAYED", "deprovision_request", request_id,
                      {"status": current["status"]})
            db.commit()
            return current, True
        deny("INVALID_STATE",
             f"Cannot execute a request that is {current['status'] if current else 'UNKNOWN'}",
             409, "INVALID_STATE",
             {"current_status": current["status"] if current else None})

    log_event(db, actor, "DEPROVISION_EXECUTING", "deprovision_request", request_id,
              {"system": req["system"], "external_account_id": req["external_account_id"],
               "action": "DISABLE"})
    db.commit()

    # 6. Call executor to disable account (disable only, never delete)
    claimed_success = False
    action_result = None
    error_msg = None
    try:
        action_result = connector.disable_account(req["system"], req["external_account_id"])
        claimed_success = bool(action_result.success)
    except ConnectorError as exc:
        error_msg = str(exc)
        claimed_success = False
    except Exception as exc:
        error_msg = str(exc)
        claimed_success = False

    resp_data = action_result.to_dict() if action_result else {"error": error_msg}
    requests_repo.record_execution(db, request_id, utcnow_iso(), resp_data, claimed_success)

    if not claimed_success:
        requests_repo.transition_status(
            db, request_id, RequestStatus.EXECUTING.value, RequestStatus.EXECUTION_FAILED.value)
        log_event(db, actor, "DEPROVISION_EXECUTION_FAILED", "deprovision_request", request_id,
                  {"system": req["system"], "external_account_id": req["external_account_id"],
                   "error": error_msg or (action_result.message if action_result else "Execution failed")})
        db.commit()
        return requests_repo.get(db, request_id), False

    # 7. Connector claimed success -> transition to EXECUTED_UNVERIFIED
    requests_repo.transition_status(
        db, request_id, RequestStatus.EXECUTING.value, RequestStatus.EXECUTED_UNVERIFIED.value)
    log_event(db, actor, "DEPROVISION_EXECUTED", "deprovision_request", request_id,
              {"system": req["system"], "external_account_id": req["external_account_id"],
               "claim": resp_data})
    db.commit()

    # 8. Independent post-execution verification: fresh read from connector
    verify_ts = utcnow_iso()
    try:
        observed_account = connector.get_account(req["system"], req["external_account_id"])
    except Exception as exc:
        observed_account = None

    observed_status = observed_account.status.value if observed_account else None
    passed = (observed_account is not None and observed_account.status == AccountStatus.DISABLED)
    raw_data = observed_account.to_dict() if observed_account else None

    requests_repo.record_verification(db, request_id, verify_ts, observed_status, passed, raw_data)

    if passed:
        requests_repo.transition_status(
            db, request_id, RequestStatus.EXECUTED_UNVERIFIED.value, RequestStatus.VERIFIED.value,
            verified_at=verify_ts)
        log_event(db, actor, "DEPROVISION_VERIFIED", "deprovision_request", request_id,
                  {"system": req["system"], "external_account_id": req["external_account_id"],
                   "observed_status": observed_status})
        db.commit()
    else:
        requests_repo.transition_status(
            db, request_id, RequestStatus.EXECUTED_UNVERIFIED.value, RequestStatus.VERIFICATION_FAILED.value)
        log_event(db, actor, "DEPROVISION_VERIFICATION_FAILED", "deprovision_request", request_id,
                  {"system": req["system"], "external_account_id": req["external_account_id"],
                   "observed_status": observed_status,
                   "reason": "Account is not DISABLED upon fresh post-execution verification"})
        db.commit()

    return requests_repo.get(db, request_id), False

