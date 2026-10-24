"""Scan orchestration: read HR + SaaS, match, classify, record findings with evidence.

READ-ONLY with respect to the SaaS side: a scan never calls disable_account (or anything that mutates
a connector). Deprovisioning is a separate, human-approved workflow (Stages 3-4).
"""
from __future__ import annotations

import sqlite3

from ..connectors.base import ConnectorError, HRSource, SaaSConnector
from ..repositories import accounts as accounts_repo
from ..repositories import employees as employees_repo
from ..repositories import exclusions as exclusions_repo
from ..repositories import findings as findings_repo
from ..repositories import scans as scans_repo
from ..utils import utcnow_iso
from .audit_service import log_event
from .classification import build_evidence, classify, exclusion_rules
from .matching import EmployeeIndex, MatchResult, match_account

_SKIPPED = MatchResult(employee=None, method=None, confidence=None, needs_review=False,
                       note="Excluded before identity matching", rationale={})


class ScanFailed(Exception):
    """A source (HR or SaaS connector) could not be read. The scan is recorded as FAILED."""

    def __init__(self, scan_id: int, cause: Exception):
        super().__init__(f"Scan {scan_id} failed: {cause}")
        self.scan_id = scan_id
        self.cause = cause


def run_scan(db: sqlite3.Connection, connector: SaaSConnector, hr_source: HRSource, actor: str) -> dict:
    scan_id = scans_repo.create(db, utcnow_iso(), connector.name)
    log_event(db, actor, "SCAN_STARTED", "scan", scan_id, {"connector": connector.name})
    db.commit()   # the scan row survives even if the scan fails below

    try:
        employees = hr_source.list_employees()
        accounts = connector.list_accounts()          # fresh live read
        exclusions = exclusions_repo.load_map(db)
        index = EmployeeIndex(employees)

        employees_repo.upsert_many(db, employees)
        created_at = utcnow_iso()
        for account in accounts:
            account_id = accounts_repo.insert_snapshot(db, scan_id, account)
            rules = exclusion_rules(account, exclusions)
            match = _SKIPPED if rules else match_account(account, index)
            classification, reason = classify(account, match, rules)
            finding_id = findings_repo.insert_finding(
                db, scan_id, account_id,
                match.employee.employee_id if match.employee else None,
                classification, match.method, match.confidence, reason, created_at)
            for etype, detail in build_evidence(account, match, rules):
                findings_repo.insert_evidence(db, finding_id, etype, detail, created_at)

        summary = {
            "employees_synced": len(employees),
            "total_accounts": len(accounts),
            "systems": sorted({a.system for a in accounts}),
            "by_classification": findings_repo.counts_by_classification(db, scan_id),
        }
        scans_repo.mark_completed(db, scan_id, utcnow_iso(), summary)
        log_event(db, actor, "SCAN_COMPLETED", "scan", scan_id, summary)
        db.commit()
    except Exception as exc:
        db.rollback()   # discard partial findings
        error = f"{type(exc).__name__}: {exc}"
        scans_repo.mark_failed(db, scan_id, utcnow_iso(), error)
        log_event(db, actor, "SCAN_FAILED", "scan", scan_id, {"error": error})
        db.commit()
        if isinstance(exc, ConnectorError):
            raise ScanFailed(scan_id, exc) from exc
        raise

    return scans_repo.get(db, scan_id)
