from __future__ import annotations

import json
import sqlite3

from ..models import Classification, EvidenceType, MatchConfidence, MatchMethod

_SELECT = """
SELECT f.id AS f_id, f.scan_id, f.classification, f.match_method, f.match_confidence, f.reason, f.created_at,
       a.id AS a_id, a.system, a.external_account_id, a.email AS a_email, a.display_name, a.username,
       a.employee_id AS a_employee_id, a.account_type, a.status AS a_status, a.last_login_at,
       e.employee_id AS e_id, e.full_name, e.work_email, e.employment_status, e.termination_date, e.department
FROM findings f
JOIN accounts a ON a.id = f.account_id
LEFT JOIN employees e ON e.employee_id = f.employee_id
"""


def _to_dict(r: sqlite3.Row) -> dict:
    employee = None
    if r["e_id"] is not None:
        employee = {"employee_id": r["e_id"], "full_name": r["full_name"], "work_email": r["work_email"],
                    "employment_status": r["employment_status"], "termination_date": r["termination_date"],
                    "department": r["department"]}
    return {
        "id": r["f_id"], "scan_id": r["scan_id"], "classification": r["classification"],
        "match_method": r["match_method"], "match_confidence": r["match_confidence"],
        "reason": r["reason"], "created_at": r["created_at"], "employee": employee,
        "account": {"id": r["a_id"], "system": r["system"], "external_account_id": r["external_account_id"],
                    "email": r["a_email"], "display_name": r["display_name"], "username": r["username"],
                    "employee_id": r["a_employee_id"], "account_type": r["account_type"],
                    "status": r["a_status"], "last_login_at": r["last_login_at"]},
    }


def insert_finding(db: sqlite3.Connection, scan_id: int, account_id: int, employee_id: str | None,
                   classification: Classification, method: MatchMethod | None,
                   confidence: MatchConfidence | None, reason: str, created_at: str) -> int:
    cur = db.execute(
        "INSERT INTO findings (scan_id, account_id, employee_id, classification, match_method, match_confidence, "
        "reason, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (scan_id, account_id, employee_id, classification.value, method.value if method else None,
         confidence.value if confidence else None, reason, created_at))
    return cur.lastrowid


def insert_evidence(db: sqlite3.Connection, finding_id: int, etype: EvidenceType, detail: dict, created_at: str) -> None:
    db.execute("INSERT INTO evidence (finding_id, type, detail_json, created_at) VALUES (?,?,?,?)",
               (finding_id, etype.value, json.dumps(detail, sort_keys=True), created_at))


def list_findings(db: sqlite3.Connection, scan_id: int, classification: str | None = None,
                  system: str | None = None) -> list[dict]:
    sql, params = _SELECT + " WHERE f.scan_id = ?", [scan_id]
    if classification:
        sql += " AND f.classification = ?"
        params.append(classification)
    if system:
        sql += " AND a.system = ?"
        params.append(system)
    return [_to_dict(r) for r in db.execute(sql + " ORDER BY f.id", params)]


def get_finding(db: sqlite3.Connection, finding_id: int) -> dict | None:
    row = db.execute(_SELECT + " WHERE f.id = ?", (finding_id,)).fetchone()
    if row is None:
        return None
    finding = _to_dict(row)
    finding["evidence"] = [
        {"id": e["id"], "type": e["type"], "detail": json.loads(e["detail_json"]), "created_at": e["created_at"]}
        for e in db.execute("SELECT * FROM evidence WHERE finding_id = ? ORDER BY id", (finding_id,))]
    return finding


def counts_by_classification(db: sqlite3.Connection, scan_id: int) -> dict[str, int]:
    counts = {c.value: 0 for c in Classification}
    for r in db.execute("SELECT classification, COUNT(*) AS n FROM findings WHERE scan_id = ? GROUP BY classification",
                        (scan_id,)):
        counts[r["classification"]] = r["n"]
    return counts
