from __future__ import annotations

import json
import sqlite3


def _to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["summary"] = json.loads(d.pop("summary_json")) if d.get("summary_json") else None
    return d


def create(db: sqlite3.Connection, started_at: str, connector: str) -> int:
    cur = db.execute("INSERT INTO scans (started_at, connector, status) VALUES (?,?,'RUNNING')",
                     (started_at, connector))
    return cur.lastrowid


def mark_completed(db: sqlite3.Connection, scan_id: int, finished_at: str, summary: dict) -> None:
    db.execute("UPDATE scans SET status='COMPLETED', finished_at=?, summary_json=? WHERE id=?",
               (finished_at, json.dumps(summary, sort_keys=True), scan_id))


def mark_failed(db: sqlite3.Connection, scan_id: int, finished_at: str, error: str) -> None:
    db.execute("UPDATE scans SET status='FAILED', finished_at=?, summary_json=? WHERE id=?",
               (finished_at, json.dumps({"error": error}), scan_id))


def get(db: sqlite3.Connection, scan_id: int) -> dict | None:
    row = db.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
    return _to_dict(row) if row else None


def list_all(db: sqlite3.Connection) -> list[dict]:
    return [_to_dict(r) for r in db.execute("SELECT * FROM scans ORDER BY id DESC")]


def latest_completed(db: sqlite3.Connection) -> dict | None:
    row = db.execute("SELECT * FROM scans WHERE status='COMPLETED' ORDER BY id DESC LIMIT 1").fetchone()
    return _to_dict(row) if row else None
