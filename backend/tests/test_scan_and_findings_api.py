import unittest

from app.connectors.base import ConnectorError
from app.connectors.synthetic import SyntheticConnector
from tests.base import ACTOR, AppTestCase


class SpyConnector(SyntheticConnector):
    """Records every mutating call so we can prove a scan never changes anything."""
    def __init__(self, path):
        self.disable_calls = []
        super().__init__(path)

    def disable_account(self, system, external_account_id):
        self.disable_calls.append((system, external_account_id))
        return super().disable_account(system, external_account_id)


class FailingConnector(SyntheticConnector):
    def list_accounts(self, system=None):
        raise ConnectorError("console unreachable")


class ScanApiTests(AppTestCase):
    def test_scan_requires_actor(self):
        r = self.client.post("/api/v1/scans")
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (400, "ACTOR_REQUIRED"))

    def test_scan_is_read_only_and_never_disables_anything(self):
        spy = SpyConnector(self.config.synthetic_data_dir + "/accounts.json")
        self.app.extensions["connector"] = spy
        before = spy.list_accounts()
        self.run_scan()
        self.assertEqual(spy.disable_calls, [])
        self.assertEqual(spy.list_accounts(), before)

    def test_scan_writes_audit_trail(self):
        self.run_scan()
        events = [r["event"] for r in self.raw_db().execute(
            "SELECT event FROM audit_log WHERE entity_type='scan' ORDER BY id")]
        self.assertEqual(events, ["SCAN_STARTED", "SCAN_COMPLETED"])
        actor = self.raw_db().execute("SELECT DISTINCT actor FROM audit_log").fetchone()[0]
        self.assertEqual(actor, ACTOR["X-Actor"])

    def test_scan_failure_is_recorded_and_leaves_no_partial_findings(self):
        self.app.extensions["connector"] = FailingConnector(self.config.synthetic_data_dir + "/accounts.json")
        r = self.client.post("/api/v1/scans", headers=ACTOR)
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.get_json()["error"]["code"], "SOURCE_UNAVAILABLE")
        db = self.raw_db()
        scan = db.execute("SELECT status, summary_json FROM scans").fetchone()
        self.assertEqual(scan["status"], "FAILED")
        self.assertIn("console unreachable", scan["summary_json"])
        self.assertEqual(db.execute("SELECT COUNT(*) FROM findings").fetchone()[0], 0)
        events = [x["event"] for x in db.execute("SELECT event FROM audit_log ORDER BY id")]
        self.assertEqual(events, ["SCAN_STARTED", "SCAN_FAILED"])

    def test_failed_scan_is_not_used_as_the_default_findings_scan(self):
        good = self.run_scan()
        self.app.extensions["connector"] = FailingConnector(self.config.synthetic_data_dir + "/accounts.json")
        self.client.post("/api/v1/scans", headers=ACTOR)
        r = self.client.get("/api/v1/findings").get_json()
        self.assertEqual(r["meta"]["scan_id"], good["id"])

    def test_list_and_get_scans(self):
        first, second = self.run_scan(), self.run_scan()
        listed = self.client.get("/api/v1/scans").get_json()["data"]
        self.assertEqual([s["id"] for s in listed], [second["id"], first["id"]])   # newest first
        self.assertEqual(self.client.get(f"/api/v1/scans/{first['id']}").get_json()["data"]["status"], "COMPLETED")
        r = self.client.get("/api/v1/scans/999")
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (404, "NOT_FOUND"))

    def test_employees_are_synced_from_hr_on_scan(self):
        self.assertEqual(self.raw_db().execute("SELECT COUNT(*) FROM employees").fetchone()[0], 0)
        self.run_scan()
        self.assertEqual(self.raw_db().execute("SELECT COUNT(*) FROM employees").fetchone()[0], 7)
        self.run_scan()   # upsert, not duplicate
        self.assertEqual(self.raw_db().execute("SELECT COUNT(*) FROM employees").fetchone()[0], 7)


class FindingsApiTests(AppTestCase):
    def test_no_scan_yet_returns_empty_list(self):
        r = self.client.get("/api/v1/findings").get_json()
        self.assertEqual((r["data"], r["meta"]), ([], {"scan_id": None, "count": 0}))

    def test_default_is_latest_scan_only(self):
        self.run_scan()
        second = self.run_scan()
        r = self.client.get("/api/v1/findings").get_json()
        self.assertEqual((r["meta"]["scan_id"], r["meta"]["count"]), (second["id"], 16))
        self.assertTrue(all(f["scan_id"] == second["id"] for f in r["data"]))

    def test_explicit_scan_id_returns_that_scan(self):
        first = self.run_scan()
        self.run_scan()
        r = self.client.get(f"/api/v1/findings?scan_id={first['id']}").get_json()
        self.assertTrue(all(f["scan_id"] == first["id"] for f in r["data"]))

    def test_filters(self):
        self.run_scan()
        self.assertEqual(len(self.findings(classification="LEAVER_ACTIVE")), 7)
        self.assertEqual(len(self.findings(system="Jira")), 5)
        self.assertEqual(len(self.findings(system="Jira", classification="LEAVER_ACTIVE")), 3)
        self.assertEqual(self.findings(system="Nope"), [])

    def test_validation_and_not_found_errors(self):
        self.run_scan()
        for url, status, code in (("/api/v1/findings?classification=BOGUS", 422, "VALIDATION_ERROR"),
                                  ("/api/v1/findings?scan_id=abc", 422, "VALIDATION_ERROR"),
                                  ("/api/v1/findings?scan_id=999", 404, "NOT_FOUND"),
                                  ("/api/v1/findings/9999", 404, "NOT_FOUND")):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (status, code))

    def test_list_items_have_contract_shape_without_evidence(self):
        self.run_scan()
        f = self.findings()[0]
        self.assertEqual(set(f), {"id", "scan_id", "classification", "match_method", "match_confidence", "reason",
                                  "created_at", "employee", "account", "deprovision_eligible"})
        self.assertEqual(set(f["account"]), {"id", "system", "external_account_id", "email", "display_name",
                                             "username", "employee_id", "account_type", "status", "last_login_at"})

    def test_detail_includes_ordered_evidence(self):
        self.run_scan()
        f = self.findings_by_account()["S-1002"]
        detail = self.finding_detail(f["id"])
        self.assertEqual([e["type"] for e in detail["evidence"]],
                         ["ACCOUNT_RECORD", "HR_RECORD", "MATCH_RATIONALE", "LAST_LOGIN"])
        self.assertTrue(all(isinstance(e["detail"], dict) for e in detail["evidence"]))

    def test_every_leaver_finding_has_evidence_for_hr_account_match_and_login(self):
        self.run_scan()
        for f in self.findings(classification="LEAVER_ACTIVE"):
            types = {e["type"] for e in self.finding_detail(f["id"])["evidence"]}
            self.assertEqual(types, {"ACCOUNT_RECORD", "HR_RECORD", "MATCH_RATIONALE", "LAST_LOGIN"})

    def test_summary_before_and_after_scan(self):
        r = self.client.get("/api/v1/summary").get_json()["data"]
        self.assertEqual((r["latest_scan"], r["total_findings"], r["leavers_active"]), (None, 0, 0))
        self.run_scan()
        r = self.client.get("/api/v1/summary").get_json()["data"]
        self.assertEqual((r["leavers_active"], r["excluded"], r["needs_review"], r["total_findings"]), (7, 4, 1, 16))
        self.assertEqual((r["pending_approval"], r["verified"]), (0, 0))
        self.assertEqual(r["findings_by_classification"]["OK"], 4)

    def test_no_execution_or_verification_endpoints_exist_yet(self):
        # Stage 3 added prepare/approve/reject, so those are no longer asserted absent here.
        # Execution and verification stay unimplemented until Stage 4.
        self.run_scan()
        for method, path in (("post", "/api/v1/deprovision-requests/1/execute"),
                             ("post", "/api/v1/deprovision-requests/1/verify")):
            self.assertEqual(getattr(self.client, method)(path, headers=ACTOR).status_code, 404, path)


if __name__ == "__main__":
    unittest.main()
