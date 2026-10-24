"""SQLite access: one connection per request, foreign keys on, schema from schema.sql."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, current_app, g

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str) -> None:
    """Create tables if missing. Safe to call on every startup; never wipes data."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def reset_schema(conn: sqlite3.Connection) -> None:
    """DEMO-ONLY: drop every table (and its triggers/indexes) and recreate an empty schema."""
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    for name in tables:
        conn.execute(f'DROP TABLE IF EXISTS "{name}"')
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["AUDITOR"].database_path)
    return g.db


def _close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app: Flask, database_path: str) -> None:
    app.teardown_appcontext(_close_db)
    init_db(database_path)
