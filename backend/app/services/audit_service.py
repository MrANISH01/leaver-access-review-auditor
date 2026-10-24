from __future__ import annotations

import json
import sqlite3

from ..utils import utcnow_iso


def log_event(db: sqlite3.Connection, actor: str, event: str, entity_type: str, entity_id: str,
              detail: dict | None = None) -> None:
    """Append an audit row. Does NOT commit: callers commit it atomically with the change it records."""
    db.execute(
        "INSERT INTO audit_log (ts, actor, event, entity_type, entity_id, detail_json) VALUES (?,?,?,?,?,?)",
        (utcnow_iso(), actor, event, entity_type, str(entity_id), json.dumps(detail or {}, sort_keys=True)))
