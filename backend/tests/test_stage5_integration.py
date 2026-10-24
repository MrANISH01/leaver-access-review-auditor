"""Stage 5 integration tests: End-to-end demo workflow, fault-injection recovery,
pre-check safeguards, audit trail integrity, and mock-admin status verification.
"""
from __future__ import annotations

import json
from dataclasses import replace

from app import create_app
from app.config import Config, ConfigError
from app.models import AccountStatus, EmploymentStatus, FaultMode
from tests.base import (
    ACTOR,
    APPROVER,
    APPROVER2,
    OUTSIDER,
    PREPARER,
    AppTestCase,
)


class Stage5DemoWorkflowIntegrationTests(AppTestCase):
    demo_mode = True
    frontend_origins = ("http://localhost:5173",)

    def test_full_end_to_end_demo_lifecycle(self):
        """Complete demo script from system reset to verified execution and audit logging."""
        # 1. System health & whoami checks
        r_health = self.client.get("/api/v1/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertTrue(r_health.get_json()["data"]["demo_mode"])

        r_whoami_approver = self.client.get("/api/v1/whoami", headers=APPROVER)
        self.assertTrue(r_whoami_approver.get_json()["data"]["can_approve"])

        r_whoami_preparer = self.client.get("/api/v1/whoami", headers=PREPARER)
        self.assertFalse(r_whoami_preparer.get_json()["data"]["can_approve"])

        # 2. Reset database and connector state
        r_reset = self.client.post("/api/v1/dev/reset", headers=ACTOR)
        self.assertEqual(r_reset.status_code, 200)
        self.assertTrue(r_reset.get_json()["data"]["reset"])

        # 3. Initial summary dashboard: pristine state
        r_sum_init = self.client.get("/api/v1/summary").get_json()["data"]
        self.assertIsNone(r_sum_init["latest_scan"])
        self.assertEqual(r_sum_init["total_findings"], 0)
        self.assertEqual(r_sum_init["pending_approval"], 0)
        self.assertEqual(r_sum_init["verified"], 0)

        # 4. Trigger read-only scan
        r_scan = self.client.post("/api/v1/scans", headers=ACTOR)
        self.assertEqual(r_scan.status_code, 201)
        scan_id = r_scan.get_json()["data"]["id"]

        # 5. Verify post-scan summary counts
        r_sum_post = self.client.get("/api/v1/summary").get_json()["data"]
        self.assertEqual(r_sum_post["total_findings"], 16)
        self.assertEqual(r_sum_post["leavers_active"], 7)
        self.assertEqual(r_sum_post["excluded"], 4)
        self.assertEqual(r_sum_post["needs_review"], 1)

        # 6. Verify leaver findings with evidence
        r_findings = self.client.get("/api/v1/findings?classification=LEAVER_ACTIVE").get_json()["data"]
        self.assertEqual(len(r_findings), 7)
        leaver_account_ids = {f["account"]["external_account_id"] for f in r_findings}
        self.assertIn("S-1001", leaver_account_ids)   # Rahul (Slack)
        self.assertIn("S-1002", leaver_account_ids)   # Priya (Slack surname change)

        # Inspect finding detail with rich evidence
        priya_finding = next(f for f in r_findings if f["account"]["external_account_id"] == "S-1002")
        r_detail = self.client.get(f"/api/v1/findings/{priya_finding['id']}").get_json()["data"]
        self.assertEqual(r_detail["classification"], "LEAVER_ACTIVE")
        evidence_types = {e["type"] for e in r_detail["evidence"]}
        self.assertTrue({"HR_RECORD", "ACCOUNT_RECORD", "MATCH_RATIONALE"} <= evidence_types)

        # 7. Exclusions verification: shared/service accounts excluded
        r_excluded = self.client.get("/api/v1/findings?classification=EXCLUDED").get_json()["data"]
        self.assertEqual(len(r_excluded), 4)
        for excl in r_excluded:
            self.assertFalse(excl["deprovision_eligible"])

        # 8. Deprovision request preparation: Rahul's Slack account S-1001
        rahul_finding = next(f for f in r_findings if f["account"]["external_account_id"] == "S-1001")
        r_prep = self.client.post(f"/api/v1/findings/{rahul_finding['id']}/deprovision-requests",
                                  headers=PREPARER)
        self.assertEqual(r_prep.status_code, 201)
        req_id = r_prep.get_json()["data"]["id"]
        self.assertEqual(r_prep.get_json()["data"]["status"], "PREPARED")

        # Duplicate preparation is blocked
        r_dup = self.client.post(f"/api/v1/findings/{rahul_finding['id']}/deprovision-requests",
                                 headers=PREPARER)
        self.assertEqual(r_dup.status_code, 409)
        self.assertEqual(r_dup.get_json()["error"]["code"], "DUPLICATE_REQUEST")

        # 9. Human approval safeguards:
        # 9a. Non-approver preparer cannot approve
        r_preparer_appr = self.client.post(f"/api/v1/deprovision-requests/{req_id}/approve", headers=PREPARER)
        self.assertEqual(r_preparer_appr.status_code, 403)
        self.assertEqual(r_preparer_appr.get_json()["error"]["code"], "APPROVER_NOT_AUTHORIZED")

        # 9b. Allowlisted approver cannot approve their own prepared request (Separation of Duties)
        r_prep_by_approver = self.client.post(f"/api/v1/findings/{priya_finding['id']}/deprovision-requests",
                                              headers=APPROVER)
        self.assertEqual(r_prep_by_approver.status_code, 201)
        priya_req_id = r_prep_by_approver.get_json()["data"]["id"]
        r_self_appr = self.client.post(f"/api/v1/deprovision-requests/{priya_req_id}/approve", headers=APPROVER)
        self.assertEqual(r_self_appr.status_code, 403)
        self.assertEqual(r_self_appr.get_json()["error"]["code"], "SELF_APPROVAL_FORBIDDEN")

        # 9c. Unauthorized outsider actor approval is rejected
        r_unauth = self.client.post(f"/api/v1/deprovision-requests/{req_id}/approve", headers=OUTSIDER)
        self.assertEqual(r_unauth.status_code, 403)
        self.assertEqual(r_unauth.get_json()["error"]["code"], "APPROVER_NOT_AUTHORIZED")

        # 9d. Legitimate different approver approves
        r_appr = self.client.post(f"/api/v1/deprovision-requests/{req_id}/approve", headers=APPROVER,
                                  json={"note": "Confirmed termination with HR"})
        self.assertEqual(r_appr.status_code, 200)
        self.assertEqual(r_appr.get_json()["data"]["status"], "APPROVED")

        # 10. Execution and Independent Verification
        r_exec = self.client.post(f"/api/v1/deprovision-requests/{req_id}/execute", headers=APPROVER)
        self.assertEqual(r_exec.status_code, 200)
        data_exec = r_exec.get_json()["data"]
        self.assertEqual(data_exec["status"], "VERIFIED")
        self.assertTrue(data_exec["verified"])
        self.assertIsNotNone(data_exec["executed_at"])
        self.assertIsNotNone(data_exec["verified_at"])

        # Ground truth: check connector accounts endpoint directly
        r_ground_truth = self.client.get("/api/v1/dev/connector/accounts").get_json()["data"]
        rahul_live = next(a for a in r_ground_truth if a["external_account_id"] == "S-1001")
        self.assertEqual(rahul_live["status"], "DISABLED")

        # 11. Idempotency test: repeating execution replays cleanly without secondary execution
        r_reexec = self.client.post(f"/api/v1/deprovision-requests/{req_id}/execute", headers=APPROVER)
        self.assertEqual(r_reexec.status_code, 200)
        self.assertTrue(r_reexec.get_json()["meta"]["idempotent_replay"])

        # 12. Human rejection workflow: Priya's Slack account S-1002 (withdrawn or rejected)
        r_rej = self.client.post(f"/api/v1/deprovision-requests/{priya_req_id}/reject", headers=APPROVER2,
                                 json={"note": "Legal hold requested - do not disable"})
        self.assertEqual(r_rej.status_code, 200)
        self.assertEqual(r_rej.get_json()["data"]["status"], "REJECTED")

        # Rejected request cannot be executed
        r_exec_rej = self.client.post(f"/api/v1/deprovision-requests/{priya_req_id}/execute", headers=APPROVER)
        self.assertEqual(r_exec_rej.status_code, 409)
        self.assertEqual(r_exec_rej.get_json()["error"]["code"], "INVALID_STATE")

        # 13. Audit trail verification: chronological event chain
        r_audit = self.client.get("/api/v1/audit-log").get_json()["data"]
        events = [a["event"] for a in r_audit]
        self.assertIn("DEMO_RESET", events)
        self.assertIn("SCAN_STARTED", events)
        self.assertIn("SCAN_COMPLETED", events)
        self.assertIn("DEPROVISION_PREPARED", events)
        self.assertIn("DEPROVISION_APPROVE_DENIED", events)
        self.assertIn("DEPROVISION_APPROVED", events)
        self.assertIn("DEPROVISION_EXECUTING", events)
        self.assertIn("DEPROVISION_EXECUTED", events)
        self.assertIn("DEPROVISION_VERIFIED", events)
        self.assertIn("DEPROVISION_REJECTED", events)


class Stage5FaultAndRecoveryIntegrationTests(AppTestCase):
    demo_mode = True

    def test_fault_injection_and_safe_recovery_end_to_end(self):
        """Inject silent no-op fault, verify detection and rejection, then recover safely."""
        self.client.post("/api/v1/scans", headers=ACTOR)
        findings = self.client.get("/api/v1/findings?classification=LEAVER_ACTIVE").get_json()["data"]
        f = next(item for item in findings if item["account"]["external_account_id"] == "G-2001")

        # 1. Inject fault via /dev/fault-injection
        r_fault = self.client.post("/api/v1/dev/fault-injection", headers=ACTOR,
                                   json={"mode": "silent_noop", "system": "GitHub", "external_account_id": "G-2001"})
        self.assertEqual(r_fault.status_code, 200)

        # 2. Prepare and approve request
        r_prep = self.client.post(f"/api/v1/findings/{f['id']}/deprovision-requests", headers=PREPARER)
        req_id = r_prep.get_json()["data"]["id"]
        self.client.post(f"/api/v1/deprovision-requests/{req_id}/approve", headers=APPROVER)

        # 3. Execute: connector claims success, but verifier detects failure
        r_exec = self.client.post(f"/api/v1/deprovision-requests/{req_id}/execute", headers=APPROVER)
        self.assertEqual(r_exec.status_code, 200)
        self.assertEqual(r_exec.get_json()["data"]["status"], "VERIFICATION_FAILED")
        self.assertFalse(r_exec.get_json()["data"]["verified"])

        # 4. Clear faults via DELETE /dev/fault-injection
        r_clear = self.client.delete("/api/v1/dev/fault-injection", headers=ACTOR)
        self.assertEqual(r_clear.status_code, 200)

        # 5. Safe retry: prepare new request for same account (allowed since previous is VERIFICATION_FAILED)
        r_retry_prep = self.client.post(f"/api/v1/findings/{f['id']}/deprovision-requests", headers=PREPARER)
        self.assertEqual(r_retry_prep.status_code, 201)
        retry_id = r_retry_prep.get_json()["data"]["id"]
        self.assertNotEqual(req_id, retry_id)

        # 6. Approve and execute retry -> VERIFIED
        self.client.post(f"/api/v1/deprovision-requests/{retry_id}/approve", headers=APPROVER2)
        r_retry_exec = self.client.post(f"/api/v1/deprovision-requests/{retry_id}/execute", headers=APPROVER2)
        self.assertEqual(r_retry_exec.status_code, 200)
        self.assertEqual(r_retry_exec.get_json()["data"]["status"], "VERIFIED")
        self.assertTrue(r_retry_exec.get_json()["data"]["verified"])


class Stage5ConnectorBoundaryTests(AppTestCase):
    def test_mock_admin_connector_fails_loudly_without_official_access_details(self):
        """Confirms that CONNECTOR=mock_admin is not invented and fails startup cleanly."""
        with self.assertRaises(ConfigError) as ctx:
            create_app(Config(connector="mock_admin"))
        self.assertIn("CONNECTOR=mock_admin is not implemented yet", str(ctx.exception))
        self.assertIn("official console details", str(ctx.exception))
