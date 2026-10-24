from __future__ import annotations

import json
import sqlite3


def list_events(db: sqlite3.Connection, entity_type: str | None = None, entity_id: str | None = None,
                event: str | None = None, limit: int = 200) -> list[dict]:
    """Most recent `limit` matching events, returned in chronological order."""
    clauses, params = [], []
    for column, value in (("entity_type", entity_type), ("entity_id", entity_id), ("event", event)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        f"SELECT * FROM (SELECT * FROM audit_log{where} ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
        (*params, limit))
    return [{"id": r["id"], "ts": r["ts"], "actor": r["actor"], "event": r["event"],
             "entity_type": r["entity_type"], "entity_id": r["entity_id"],
             "detail": json.loads(r["detail_json"]) if r["detail_json"] else {}} for r in rows]
