"""Shared test fixtures. unittest-style so they run under both pytest and `python -m unittest`."""
import json
import os
import sqlite3
import tempfile
import unittest

from app import create_app
from app.config import Config, DEFAULT_DATA_DIR

ACTOR = {"X-Actor": "tester@acme.example"}
PREPARER = {"X-Actor": "preparer@acme.example"}      # may prepare; NOT on the approver allowlist
APPROVER = {"X-Actor": "approver@acme.example"}      # on the allowlist
APPROVER2 = {"X-Actor": "approver2@acme.example"}    # on the allowlist
OUTSIDER = {"X-Actor": "mallory@acme.example"}       # on nothing
APPROVERS = ("approver@acme.example", "approver2@acme.example")


class AppTestCase(unittest.TestCase):
    demo_mode = False
    frontend_origins: tuple = ()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmpdir = tmp.name
        self.db_path = os.path.join(tmp.name, "test.sqlite3")
        self.config = Config(
            database_path=self.db_path, connector="synthetic", hr_source="synthetic",
            demo_mode=self.demo_mode, frontend_origins=tuple(self.frontend_origins),
            synthetic_data_dir=str(DEFAULT_DATA_DIR), approver_actors=APPROVERS)
        self.app = create_app(self.config)
        self.app.testing = True
        self.client = self.app.test_client()
        self.connector = self.app.extensions["connector"]

    def raw_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        self.addCleanup(conn.close)
        return conn

    # ---- helpers for scan/findings tests ----
    def use_data(self, employees=None, accounts=None, exclusions=None):
        """Rebuild the app on custom synthetic data (JSON-compatible lists of dicts)."""
        import dataclasses
        data_dir = os.path.join(self.tmpdir, "custom_data")
        os.makedirs(data_dir, exist_ok=True)
        for name, rows in (("employees.json", employees or []), ("accounts.json", accounts or []),
                           ("exclusions.json", exclusions or [])):
            with open(os.path.join(data_dir, name), "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
        self.db_path = os.path.join(self.tmpdir, "custom.sqlite3")
        self.config = dataclasses.replace(self.config, database_path=self.db_path, synthetic_data_dir=data_dir)
        self.app = create_app(self.config)
        self.app.testing = True
        self.client = self.app.test_client()
        self.connector = self.app.extensions["connector"]

    def run_scan(self):
        r = self.client.post("/api/v1/scans", headers=ACTOR)
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        return r.get_json()["data"]

    def findings(self, **params):
        r = self.client.get("/api/v1/findings", query_string=params)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        return r.get_json()["data"]

    def findings_by_account(self, **params):
        return {f["account"]["external_account_id"]: f for f in self.findings(**params)}

    def finding_detail(self, finding_id):
        r = self.client.get(f"/api/v1/findings/{finding_id}")
        self.assertEqual(r.status_code, 200)
        return r.get_json()["data"]

    def evidence_of(self, finding, etype):
        return [e["detail"] for e in self.finding_detail(finding["id"])["evidence"] if e["type"] == etype]


def emp(eid, name, email, status="TERMINATED", term="2026-09-01"):
    return {"employee_id": eid, "full_name": name, "work_email": email, "employment_status": status,
            "termination_date": term if status == "TERMINATED" else None, "department": "X"}


def acct(aid, email, name, system="Slack", atype="INDIVIDUAL", status="ACTIVE", login=None, employee_id=None):
    row = {"system": system, "external_account_id": aid, "email": email, "display_name": name,
           "username": aid, "account_type": atype, "status": status, "last_login_at": login}
    if employee_id:
        row["employee_id"] = employee_id
    return row


class RequestTestCase(AppTestCase):
    """Helpers for the Stage 3 workflow tests. Runs one scan in setUp."""

    def setUp(self):
        super().setUp()
        self.run_scan()
        self.by_account = self.findings_by_account()

    def finding_id(self, external_account_id):
        return self.by_account[external_account_id]["id"]

    def prepare(self, external_account_id="S-1001", headers=PREPARER, client=None):
        return (client or self.client).post(
            f"/api/v1/findings/{self.finding_id(external_account_id)}/deprovision-requests", headers=headers)

    def prepared_id(self, external_account_id="S-1001", headers=PREPARER):
        r = self.prepare(external_account_id, headers)
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        return r.get_json()["data"]["id"]

    def decide(self, request_id, action, headers=APPROVER, note=None, client=None):
        kwargs = {"json": {"note": note}} if note is not None else {}
        return (client or self.client).post(f"/api/v1/deprovision-requests/{request_id}/{action}",
                                            headers=headers, **kwargs)

    def execute(self, request_id, headers=APPROVER, client=None):
        return (client or self.client).post(f"/api/v1/deprovision-requests/{request_id}/execute",
                                            headers=headers)


    def request_row(self, request_id):
        return self.raw_db().execute("SELECT * FROM deprovision_requests WHERE id=?", (request_id,)).fetchone()

    def audit(self, event=None, entity_type=None, entity_id=None):
        sql, params = "SELECT * FROM audit_log WHERE 1=1", []
        if event:
            sql += " AND event=?"
            params.append(event)
        if entity_type:
            sql += " AND entity_type=?"
            params.append(entity_type)
        if entity_id:
            sql += " AND entity_id=?"
            params.append(str(entity_id))
        return list(self.raw_db().execute(sql + " ORDER BY id", params))

    def connector_status(self, system, account_id):
        return self.connector.get_account(system, account_id).status.value


def install_spy(test_case):
    """Replace the app's connector with one that records every disable_account call."""
    from app.connectors.synthetic import SyntheticConnector

    class Spy(SyntheticConnector):
        def __init__(self, path):
            self.disable_calls = []
            super().__init__(path)

        def disable_account(self, system, external_account_id):
            self.disable_calls.append((system, external_account_id))
            return super().disable_account(system, external_account_id)

    spy = Spy(os.path.join(test_case.config.synthetic_data_dir, "accounts.json"))
    test_case.app.extensions["connector"] = spy
    test_case.connector = spy
    return spy
