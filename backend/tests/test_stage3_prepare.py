"""Stage 3: preparing deprovisioning requests (eligibility, no side effects, duplicates, audit)."""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from tests.base import APPROVER, PREPARER, RequestTestCase, install_spy


class PrepareTests(RequestTestCase):
    def test_prepare_creates_a_prepared_disable_request(self):
        r = self.prepare("S-1001")
        self.assertEqual(r.status_code, 201)
        d = r.get_json()["data"]
        self.assertEqual((d["status"], d["action"], d["expected_status"]), ("PREPARED", "DISABLE", "DISABLED"))
        self.assertEqual((d["system"], d["external_account_id"]), ("Slack", "S-1001"))
        self.assertEqual(d["prepared_by"], PREPARER["X-Actor"])
        self.assertIsNone(d["decided_by"])
        self.assertIsNone(d["executed_at"])
        self.assertFalse(d["verified"])
        self.assertTrue(d["idempotency_key"].startswith("deprov-"))
        self.assertEqual(d["finding"]["employee"]["employee_id"], "E101")
        self.assertEqual((d["executions"], d["verifications"]), ([], []))

    def test_prepare_requires_actor(self):
        r = self.client.post(f"/api/v1/findings/{self.finding_id('S-1001')}/deprovision-requests")
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (400, "ACTOR_REQUIRED"))

    def test_prepare_never_disables_the_account(self):
        spy = install_spy(self)
        self.prepare("S-1001")
        self.assertEqual(spy.disable_calls, [])
        self.assertEqual(self.connector_status("Slack", "S-1001"), "ACTIVE")
        statuses = {f["account"]["external_account_id"]: f["account"]["status"] for f in self.findings()}
        self.assertEqual(statuses["S-1001"], "ACTIVE")   # the stored snapshot is unchanged too

    def test_only_eligible_findings_can_have_a_request(self):
        refused = {
            "G-2005": "NEEDS_REVIEW",   # name-only match
            "S-1005": "EXCLUDED",       # service account
            "J-3003": "EXCLUDED",       # shared account
            "S-1006": "EXCLUDED",       # explicit exclusions-table entry
            "S-1003": "OK",             # active employee
            "S-1004": "OK",             # leaver whose account is already disabled
        }
        for account_id, classification in refused.items():
            with self.subTest(account=account_id):
                r = self.prepare(account_id)
                self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (422, "NOT_ELIGIBLE"))
                self.assertEqual(r.get_json()["error"]["details"]["classification"], classification)
        self.assertEqual(self.raw_db().execute("SELECT COUNT(*) FROM deprovision_requests").fetchone()[0], 0)
        denied = self.audit("DEPROVISION_PREPARE_DENIED")
        self.assertEqual(len(denied), len(refused))
        self.assertTrue(all(row["entity_type"] == "finding" and row["actor"] == PREPARER["X-Actor"] for row in denied))

    def test_every_eligible_finding_can_be_prepared(self):
        eligible = [f for f in self.findings() if f["deprovision_eligible"]]
        self.assertEqual(len(eligible), 7)
        for f in eligible:
            r = self.client.post(f"/api/v1/findings/{f['id']}/deprovision-requests", headers=PREPARER)
            self.assertEqual(r.status_code, 201, f["account"]["external_account_id"])

    def test_unknown_finding_is_404_and_audited(self):
        r = self.client.post("/api/v1/findings/9999/deprovision-requests", headers=PREPARER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (404, "NOT_FOUND"))
        (row,) = self.audit("DEPROVISION_PREPARE_DENIED")
        self.assertEqual((row["entity_id"], row["actor"]), ("9999", PREPARER["X-Actor"]))

    def test_stale_finding_from_an_older_scan_is_refused(self):
        old_id = self.finding_id("S-1001")
        self.run_scan()
        r = self.client.post(f"/api/v1/findings/{old_id}/deprovision-requests", headers=PREPARER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "STALE_FINDING"))
        fresh = self.findings_by_account()["S-1001"]
        r = self.client.post(f"/api/v1/findings/{fresh['id']}/deprovision-requests", headers=PREPARER)
        self.assertEqual(r.status_code, 201)

    def test_exclusion_added_after_the_scan_still_blocks_preparation(self):
        db = self.raw_db()
        db.execute("INSERT INTO exclusions (system, external_account_id, reason, added_by, added_at) "
                   "VALUES ('Slack','S-1001','Owner says shared','it@acme.example','t')")
        db.commit()
        r = self.prepare("S-1001")
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (422, "NOT_ELIGIBLE"))
        self.assertEqual(self.audit("DEPROVISION_PREPARE_DENIED")[0]["detail_json"].count("EXPLICITLY_EXCLUDED"), 1)

    # ---- duplicates ----
    def test_duplicate_open_request_is_refused_with_the_existing_id(self):
        first = self.prepared_id("S-1001")
        r = self.prepare("S-1001", headers=APPROVER)   # even from a different person
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "DUPLICATE_REQUEST"))
        self.assertEqual(r.get_json()["error"]["details"], {"existing_request_id": first, "existing_status": "PREPARED"})
        self.assertEqual(self.raw_db().execute("SELECT COUNT(*) FROM deprovision_requests").fetchone()[0], 1)
        (row,) = self.audit("DEPROVISION_PREPARE_DENIED")
        self.assertIn("DUPLICATE_REQUEST", row["detail_json"])

    def test_duplicate_is_refused_even_after_approval(self):
        self.client.post(f"/api/v1/deprovision-requests/{self.prepared_id('S-1001')}/approve", headers=APPROVER)
        self.assertEqual(self.prepare("S-1001").status_code, 409)

    def test_duplicate_across_scans_is_refused(self):
        # A rescan creates a NEW finding row for the same account; the account-level guard still applies.
        self.prepared_id("S-1001")
        self.run_scan()
        fresh = self.findings_by_account()["S-1001"]
        r = self.client.post(f"/api/v1/findings/{fresh['id']}/deprovision-requests", headers=PREPARER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "DUPLICATE_REQUEST"))

    def test_a_rejected_request_frees_the_account_for_a_new_one(self):
        first = self.prepared_id("S-1001")
        self.assertEqual(self.decide(first, "reject").status_code, 200)
        second = self.prepared_id("S-1001")
        self.assertNotEqual(first, second)

    def test_simultaneous_prepares_create_exactly_one_request(self):
        barrier = threading.Barrier(2)
        fid = self.finding_id("S-1001")

        def go(_):
            client = self.app.test_client()
            barrier.wait()
            return client.post(f"/api/v1/findings/{fid}/deprovision-requests", headers=PREPARER).status_code

        with ThreadPoolExecutor(2) as ex:
            codes = sorted(ex.map(go, range(2)))
        self.assertEqual(codes, [201, 409])
        self.assertEqual(self.raw_db().execute("SELECT COUNT(*) FROM deprovision_requests").fetchone()[0], 1)

    # ---- reading ----
    def test_audit_trail_for_a_successful_prepare(self):
        rid = self.prepared_id("G-2001")
        (row,) = self.audit("DEPROVISION_PREPARED")
        self.assertEqual((row["actor"], row["entity_type"], row["entity_id"]),
                         (PREPARER["X-Actor"], "deprovision_request", str(rid)))
        self.assertIn('"action": "DISABLE"', row["detail_json"])
        self.assertIn("GitHub", row["detail_json"])

    def test_list_filter_and_detail(self):
        a, b = self.prepared_id("S-1001"), self.prepared_id("G-2001")
        self.decide(a, "approve")
        listed = self.client.get("/api/v1/deprovision-requests").get_json()["data"]
        self.assertEqual([r["id"] for r in listed], [b, a])   # newest first
        only = self.client.get("/api/v1/deprovision-requests?status=APPROVED").get_json()["data"]
        self.assertEqual([r["id"] for r in only], [a])
        detail = self.client.get(f"/api/v1/deprovision-requests/{b}").get_json()["data"]
        self.assertEqual(detail["status"], "PREPARED")
        self.assertEqual(self.client.get("/api/v1/deprovision-requests?status=BOGUS").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/deprovision-requests/9999").status_code, 404)

    def test_summary_pending_approval_tracks_prepared_requests(self):
        rid = self.prepared_id("S-1001")
        self.prepared_id("G-2001")
        s = self.client.get("/api/v1/summary").get_json()["data"]
        self.assertEqual((s["pending_approval"], s["verified"]), (2, 0))
        self.decide(rid, "approve")
        self.assertEqual(self.client.get("/api/v1/summary").get_json()["data"]["pending_approval"], 1)


if __name__ == "__main__":
    unittest.main()
