"""Seeding helpers: explicit exclusions at startup, and the demo-only wipe-and-reseed."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..config import Config
from ..connectors.base import HRSource
from ..db import connect, reset_schema
from ..repositories import employees as employees_repo
from ..repositories import exclusions as exclusions_repo
from ..utils import utcnow_iso


def _exclusion_rows(config: Config) -> list[dict]:
    with open(Path(config.synthetic_data_dir) / "exclusions.json", encoding="utf-8") as fh:
        return json.load(fh)


def seed_exclusions_if_empty(config: Config) -> int:
    """Load the explicit exclusions list on startup, only if the table is empty. Never overwrites.

    In the MVP the list comes from data/synthetic/exclusions.json. Each row records who added it,
    when and why, and scans read it from the DB.
    """
    conn = connect(config.database_path)
    try:
        if exclusions_repo.count(conn) > 0:
            return 0
        n = exclusions_repo.insert_many(conn, _exclusion_rows(config), utcnow_iso())
        conn.commit()
        return n
    finally:
        conn.close()


def reset_and_seed(db: sqlite3.Connection, hr_source: HRSource, config: Config) -> dict:
    reset_schema(db)
    employees = employees_repo.insert_many(db, hr_source.list_employees())
    exclusions = exclusions_repo.insert_many(db, _exclusion_rows(config), utcnow_iso())
    return {"employees_seeded": employees, "exclusions_seeded": exclusions}
