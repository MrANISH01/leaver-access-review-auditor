from __future__ import annotations

import json
import sqlite3

from ..models import SaaSAccount


def insert_snapshot(db: sqlite3.Connection, scan_id: int, a: SaaSAccount) -> int:
    cur = db.execute(
        "INSERT INTO accounts (scan_id, system, external_account_id, email, display_name, username, employee_id, "
        "account_type, status, last_login_at, raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (scan_id, a.system, a.external_account_id, a.email, a.display_name, a.username, a.employee_id,
         a.account_type.value, a.status.value, a.last_login_at, json.dumps(a.to_dict(), sort_keys=True)))
    return cur.lastrowid
