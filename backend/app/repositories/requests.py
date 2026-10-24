"""SQL for deprovision_requests. No business rules here: those live in services/request_service.py."""
from __future__ import annotations

import json
import sqlite3

_COLUMNS = ("id, finding_id, system, external_account_id, action, expected_status, status, idempotency_key, "
            "prepared_by, prepared_at, decided_by, decided_at, decision_note, executed_at, verified_at")

# Statuses that free the account for a new request (matches the partial unique indexes in schema.sql).
CLOSED_FOR_REUSE = ("REJECTED", "EXECUTION_FAILED", "VERIFICATION_FAILED")


def insert(db: sqlite3.Connection, finding_id: int, system: str, external_account_id: str,
           idempotency_key: str, prepared_by: str, prepared_at: str) -> int:
    cur = db.execute(
        "INSERT INTO deprovision_requests (finding_id, system, external_account_id, action, expected_status, status, "
        "idempotency_key, prepared_by, prepared_at) VALUES (?,?,?,'DISABLE','DISABLED','PREPARED',?,?,?)",
        (finding_id, system, external_account_id, idempotency_key, prepared_by, prepared_at))
    return cur.lastrowid


def get(db: sqlite3.Connection, request_id: int) -> dict | None:
    row = db.execute(f"SELECT {_COLUMNS} FROM deprovision_requests WHERE id = ?", (request_id,)).fetchone()
    return dict(row) if row else None


def list_requests(db: sqlite3.Connection, status: str | None = None) -> list[dict]:
    sql, params = f"SELECT {_COLUMNS} FROM deprovision_requests", []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    return [dict(r) for r in db.execute(sql + " ORDER BY id DESC", params)]


def find_open_for_account(db: sqlite3.Connection, system: str, external_account_id: str) -> dict | None:
    placeholders = ",".join("?" for _ in CLOSED_FOR_REUSE)
    row = db.execute(
        f"SELECT {_COLUMNS} FROM deprovision_requests WHERE system = ? AND external_account_id = ? "
        f"AND status NOT IN ({placeholders}) ORDER BY id DESC LIMIT 1",
        (system, external_account_id, *CLOSED_FOR_REUSE)).fetchone()
    return dict(row) if row else None


def decide(db: sqlite3.Connection, request_id: int, from_status: str, to_status: str,
           decided_by: str, decided_at: str, note: str | None) -> bool:
    """Atomic compare-and-set: succeeds only if the row is STILL in from_status.

    This single UPDATE is what makes concurrent or repeated decisions safe: of N racing callers,
    exactly one sees rowcount == 1.
    """
    cur = db.execute(
        "UPDATE deprovision_requests SET status = ?, decided_by = ?, decided_at = ?, decision_note = ? "
        "WHERE id = ? AND status = ?",
        (to_status, decided_by, decided_at, note, request_id, from_status))
    return cur.rowcount == 1


def list_executions(db: sqlite3.Connection, request_id: int) -> list[dict]:
    return [{"id": r["id"], "attempted_at": r["attempted_at"], "claimed_success": bool(r["claimed_success"]),
             "connector_response": json.loads(r["connector_response_json"]) if r["connector_response_json"] else None}
            for r in db.execute("SELECT * FROM executions WHERE request_id = ? ORDER BY id", (request_id,))]


def list_verifications(db: sqlite3.Connection, request_id: int) -> list[dict]:
    return [{"id": r["id"], "observed_at": r["observed_at"], "observed_status": r["observed_status"],
             "passed": bool(r["passed"]), "raw": json.loads(r["raw_json"]) if r["raw_json"] else None}
            for r in db.execute("SELECT * FROM verifications WHERE request_id = ? ORDER BY id", (request_id,))]


def record_execution(db: sqlite3.Connection, request_id: int, attempted_at: str,
                     connector_response: dict | None, claimed_success: bool) -> int:
    cur = db.execute(
        "INSERT INTO executions (request_id, attempted_at, connector_response_json, claimed_success) "
        "VALUES (?, ?, ?, ?)",
        (request_id, attempted_at,
         json.dumps(connector_response) if connector_response is not None else None,
         1 if claimed_success else 0))
    return cur.lastrowid


def record_verification(db: sqlite3.Connection, request_id: int, observed_at: str,
                        observed_status: str | None, passed: bool, raw: dict | None) -> int:
    cur = db.execute(
        "INSERT INTO verifications (request_id, observed_at, observed_status, passed, raw_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (request_id, observed_at, observed_status, 1 if passed else 0,
         json.dumps(raw) if raw is not None else None))
    return cur.lastrowid


def transition_status(db: sqlite3.Connection, request_id: int, from_status: str, to_status: str,
                      executed_at: str | None = None, verified_at: str | None = None) -> bool:
    """Atomic compare-and-set: transitions status from from_status to to_status."""
    sql = "UPDATE deprovision_requests SET status = ?"
    params: list = [to_status]
    if executed_at is not None:
        sql += ", executed_at = ?"
        params.append(executed_at)
    if verified_at is not None:
        sql += ", verified_at = ?"
        params.append(verified_at)
    sql += " WHERE id = ? AND status = ?"
    params.extend([request_id, from_status])
    cur = db.execute(sql, params)
    return cur.rowcount == 1

