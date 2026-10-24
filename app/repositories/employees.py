from __future__ import annotations

import sqlite3
from typing import Iterable

from ..models import Employee


def insert_many(db: sqlite3.Connection, employees: Iterable[Employee]) -> int:
    rows = [
        (e.employee_id, e.full_name, e.work_email, e.employment_status.value, e.termination_date, e.department)
        for e in employees
    ]
    db.executemany(
        "INSERT INTO employees (employee_id, full_name, work_email, employment_status, termination_date, department) "
        "VALUES (?,?,?,?,?,?)", rows)
    return len(rows)


def upsert_many(db: sqlite3.Connection, employees: Iterable[Employee]) -> int:
    """Sync HR records into the local table (HR is the source of truth). Never deletes."""
    rows = [
        (e.employee_id, e.full_name, e.work_email, e.employment_status.value, e.termination_date, e.department)
        for e in employees
    ]
    db.executemany(
        "INSERT INTO employees (employee_id, full_name, work_email, employment_status, termination_date, department) "
        "VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(employee_id) DO UPDATE SET full_name=excluded.full_name, work_email=excluded.work_email, "
        "employment_status=excluded.employment_status, termination_date=excluded.termination_date, "
        "department=excluded.department", rows)
    return len(rows)
