from __future__ import annotations

import sqlite3


def insert_many(db: sqlite3.Connection, rows: list[dict], added_at: str) -> int:
    db.executemany(
        "INSERT INTO exclusions (system, external_account_id, reason, added_by, added_at) VALUES (?,?,?,?,?)",
        [(r["system"], r["external_account_id"], r["reason"], r["added_by"], added_at) for r in rows])
    return len(rows)


def count(db: sqlite3.Connection) -> int:
    return db.execute("SELECT COUNT(*) FROM exclusions").fetchone()[0]


def load_map(db: sqlite3.Connection) -> dict[tuple[str, str], dict]:
    rows = db.execute("SELECT system, external_account_id, reason, added_by, added_at FROM exclusions")
    return {(r["system"], r["external_account_id"]): dict(r) for r in rows}
