"""Stage 4 tests: Execution of approved requests, pre-checks, independent verification,
fault-injection (silent_noop, error, reject), idempotency, retries, and audit trail.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import replace

from app.models import AccountStatus, EmploymentStatus, FaultMode
from tests.base import (
    ACTOR,
    APPROVER,
    APPROVER2,
    OUTSIDER,
    PREPARER,
    RequestTestCase,
    install_spy,
)


class Stage4ExecutionGuardTests(RequestTestCase):
    """Execution must only run for APPROVED requests, and mandatory pre-execution checks must hold."""

    def test_execute_requires_actor_header(self):
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")
        r = self.client.post(f"/api/v1/deprovision-requests/{rid}/execute")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "ACTOR_REQUIRED")

    def test_execute_nonexistent_request_returns_404(self):
        r = self.execute(99999, headers=APPROVER)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error"]["code"], "NOT_FOUND")

    def test_prepared_request_cannot_execute(self):
        rid = self.prepared_id("S-1001")
        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["error"]["code"], "INVALID_STATE")
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")
        (denied,) = self.audit("DEPROVISION_EXECUTE_DENIED")
        self.assertEqual(denied["entity_id"], str(rid))
        self.assertIn("PREPARED", denied["detail_json"])

    def test_rejected_request_cannot_execute(self):
        rid = self.prepared_id("S-1001")
        self.decide(rid, "reject", note="Not authorized")
        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["error"]["code"], "INVALID_STATE")
        self.assertEqual(self.request_row(rid)["status"], "REJECTED")
        (denied,) = self.audit("DEPROVISION_EXECUTE_DENIED")
        self.assertIn("REJECTED", denied["detail_json"])

    def test_precheck_fails_if_employee_is_no_longer_terminated(self):
        """If HR status changed (e.g. employee was rehired / active), execution must abort."""
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")

        hr = self.app.extensions["hr_source"]
        orig_emp = hr.get_employee("E101")
        self.assertIsNotNone(orig_emp)
        # Simulate rehire / active status
        hr._employees["E101"] = replace(orig_emp, employment_status=EmploymentStatus.ACTIVE)

        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["error"]["code"], "STALE_STATE")
        self.assertIn("not TERMINATED", r.get_json()["error"]["message"])

        # SaaS account was NOT touched
        self.assertEqual(self.connector_status("Slack", "S-1001"), "ACTIVE")
        # Request remains APPROVED (not executing, not verified)
        self.assertEqual(self.request_row(rid)["status"], "APPROVED")

        (denied,) = self.audit("DEPROVISION_EXECUTE_DENIED")
        self.assertIn("EMPLOYEE_NOT_TERMINATED", denied["detail_json"])

    def test_precheck_fails_if_saas_account_is_already_disabled(self):
        """If SaaS account was already disabled out-of-band, execution must abort safely."""
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")

        # Disable out-of-band directly on connector
        self.connector.disable_account("Slack", "S-1001")
        self.assertEqual(self.connector_status("Slack", "S-1001"), "DISABLED")

        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["error"]["code"], "STALE_STATE")
        self.assertIn("not ACTIVE", r.get_json()["error"]["message"])

        # Request status remains APPROVED
        self.assertEqual(self.request_row(rid)["status"], "APPROVED")

        (denied,) = self.audit("DEPROVISION_EXECUTE_DENIED")
        self.assertIn("ACCOUNT_NOT_ACTIVE", denied["detail_json"])

    def test_precheck_fails_if_account_disappeared_from_connector(self):
        """If account was deleted on SaaS side, execution must abort safely."""
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")

        with self.connector._lock:
            del self.connector._accounts[("Slack", "S-1001")]

        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["error"]["code"], "STALE_STATE")
        self.assertIn("not found in Slack", r.get_json()["error"]["message"])
        self.assertEqual(self.request_row(rid)["status"], "APPROVED")

        (denied,) = self.audit("DEPROVISION_EXECUTE_DENIED")
        self.assertIn("ACCOUNT_NOT_FOUND", denied["detail_json"])


class Stage4ExecutionHappyPathTests(RequestTestCase):
    """Happy path: approved request executes, independent fresh read confirms DISABLED, request becomes VERIFIED."""

    def test_successful_execution_and_verification(self):
        spy = install_spy(self)
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve", note="Approved by SecOps")
        self.assertEqual(spy.disable_calls, [])

        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(body["meta"], {"idempotent_replay": False})
        data = body["data"]

        # Request state
        self.assertEqual(data["status"], "VERIFIED")
        self.assertTrue(data["verified"])
        self.assertIsNotNone(data["executed_at"])
        self.assertIsNotNone(data["verified_at"])

        # Exactly 1 disable call occurred
        self.assertEqual(spy.disable_calls, [("Slack", "S-1001")])
        self.assertEqual(self.connector_status("Slack", "S-1001"), "DISABLED")

        # Database rows
        row = self.request_row(rid)
        self.assertEqual(row["status"], "VERIFIED")
        self.assertIsNotNone(row["executed_at"])
        self.assertIsNotNone(row["verified_at"])

        # Executions table has claim
        executions = data["executions"]
        self.assertEqual(len(executions), 1)
        self.assertTrue(executions[0]["claimed_success"])
        self.assertIsNotNone(executions[0]["attempted_at"])
        self.assertEqual(executions[0]["connector_response"],
                         {"message": "Account disabled", "raw": {"status": "disabled"}, "success": True})

        # Verifications table has independent observation
        verifications = data["verifications"]
        self.assertEqual(len(verifications), 1)
        self.assertTrue(verifications[0]["passed"])
        self.assertEqual(verifications[0]["observed_status"], "DISABLED")
        self.assertIsNotNone(verifications[0]["observed_at"])
        self.assertIsNotNone(verifications[0]["raw"])

        # Audit log trail
        events = [a["event"] for a in self.audit(entity_type="deprovision_request")]
        self.assertIn("DEPROVISION_EXECUTING", events)
        self.assertIn("DEPROVISION_EXECUTED", events)
        self.assertIn("DEPROVISION_VERIFIED", events)

    def test_get_request_includes_executions_and_verifications(self):
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")
        self.execute(rid, headers=APPROVER)

        r = self.client.get(f"/api/v1/deprovision-requests/{rid}")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]
        self.assertEqual(data["status"], "VERIFIED")
        self.assertTrue(data["verified"])
        self.assertEqual(len(data["executions"]), 1)
        self.assertEqual(len(data["verifications"]), 1)

    def test_summary_dashboard_reflects_verified_count(self):
        # Initial summary
        s1 = self.client.get("/api/v1/summary").get_json()["data"]
        self.assertEqual(s1["verified"], 0)

        # Prepare, approve and execute
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")
        self.execute(rid)

        # Updated summary
        s2 = self.client.get("/api/v1/summary").get_json()["data"]
        self.assertEqual(s2["verified"], 1)

    def test_idempotent_execution_on_already_verified_request(self):
        spy = install_spy(self)
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")
        r1 = self.execute(rid, headers=APPROVER)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.get_json()["meta"]["idempotent_replay"], False)
        self.assertEqual(len(spy.disable_calls), 1)

        # Second execute call
        r2 = self.execute(rid, headers=APPROVER)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["meta"]["idempotent_replay"], True)
        self.assertEqual(r2.get_json()["data"]["status"], "VERIFIED")

        # Disable was NOT called again
        self.assertEqual(len(spy.disable_calls), 1)

        (replayed,) = self.audit("DEPROVISION_EXECUTION_REPLAYED")
        self.assertEqual(replayed["entity_id"], str(rid))


class Stage4FaultInjectionTests(RequestTestCase):
    """Fault injection: testing silent no-op (lying console), error, reject, and retry workflows."""

    def test_silent_noop_claims_success_but_independent_verification_fails(self):
        """Silent no-op: connector says success=True, but account is still ACTIVE.

        The system must NOT trust the executor claim. It must transition to VERIFICATION_FAILED.
        """
        spy = install_spy(self)
        self.connector.set_fault(FaultMode.SILENT_NOOP, "Slack", "S-1001")

        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")

        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]

        # Status must be VERIFICATION_FAILED, verified must be False
        self.assertEqual(data["status"], "VERIFICATION_FAILED")
        self.assertFalse(data["verified"])
        self.assertIsNotNone(data["executed_at"])
        self.assertIsNone(data["verified_at"])

        # Connector was called, but account is still ACTIVE
        self.assertEqual(len(spy.disable_calls), 1)
        self.assertEqual(self.connector_status("Slack", "S-1001"), "ACTIVE")

        # Executions table has the lying claim
        self.assertEqual(len(data["executions"]), 1)
        self.assertTrue(data["executions"][0]["claimed_success"])

        # Verifications table caught the truth
        self.assertEqual(len(data["verifications"]), 1)
        self.assertFalse(data["verifications"][0]["passed"])
        self.assertEqual(data["verifications"][0]["observed_status"], "ACTIVE")

        # Audit trail
        events = [a["event"] for a in self.audit(entity_type="deprovision_request", entity_id=str(rid))]
        self.assertIn("DEPROVISION_EXECUTING", events)
        self.assertIn("DEPROVISION_EXECUTED", events)
        self.assertIn("DEPROVISION_VERIFICATION_FAILED", events)
        self.assertNotIn("DEPROVISION_VERIFIED", events)

    def test_connector_error_leads_to_execution_failed(self):
        """ConnectorError during disable_account must transition to EXECUTION_FAILED."""
        self.connector.set_fault(FaultMode.ERROR, "Slack", "S-1001")

        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")

        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]

        self.assertEqual(data["status"], "EXECUTION_FAILED")
        self.assertFalse(data["verified"])
        self.assertIsNotNone(data["executed_at"])
        self.assertIsNone(data["verified_at"])

        # Executions recorded the failure
        self.assertEqual(len(data["executions"]), 1)
        self.assertFalse(data["executions"][0]["claimed_success"])
        self.assertIn("Injected fault", data["executions"][0]["connector_response"]["error"])

        # Verification did not run
        self.assertEqual(len(data["verifications"]), 0)

        # Audit trail
        events = [a["event"] for a in self.audit(entity_type="deprovision_request", entity_id=str(rid))]
        self.assertIn("DEPROVISION_EXECUTING", events)
        self.assertIn("DEPROVISION_EXECUTION_FAILED", events)
        self.assertNotIn("DEPROVISION_EXECUTED", events)
        self.assertNotIn("DEPROVISION_VERIFIED", events)

    def test_connector_reject_leads_to_execution_failed(self):
        """Connector returning success=False must transition to EXECUTION_FAILED."""
        self.connector.set_fault(FaultMode.REJECT, "Slack", "S-1001")

        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")

        r = self.execute(rid, headers=APPROVER)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]

        self.assertEqual(data["status"], "EXECUTION_FAILED")
        self.assertFalse(data["verified"])

        self.assertEqual(len(data["executions"]), 1)
        self.assertFalse(data["executions"][0]["claimed_success"])
        self.assertEqual(len(data["verifications"]), 0)

        events = [a["event"] for a in self.audit(entity_type="deprovision_request", entity_id=str(rid))]
        self.assertIn("DEPROVISION_EXECUTION_FAILED", events)

    def test_safe_retry_workflow_after_failed_execution(self):
        """When execution or verification fails, a new request may be prepared, approved, and executed.

        The database partial unique index frees the account when a request is EXECUTION_FAILED or
        VERIFICATION_FAILED, allowing a safe retry workflow.
        """
        # Step 1: Injected fault causes verification failure
        self.connector.set_fault(FaultMode.SILENT_NOOP, "Slack", "S-1001")
        rid1 = self.prepared_id("S-1001")
        self.decide(rid1, "approve")
        r1 = self.execute(rid1)
        self.assertEqual(r1.get_json()["data"]["status"], "VERIFICATION_FAILED")

        # Step 2: Cannot re-execute the failed request directly (terminal state)
        r_reexec = self.execute(rid1)
        self.assertEqual(r_reexec.status_code, 409)
        self.assertEqual(r_reexec.get_json()["error"]["code"], "INVALID_STATE")

        # Step 3: Clear the fault on the connector
        self.connector.clear_faults()

        # Step 4: Re-prepare a new request for the same account (allowed because previous request is closed)
        rid2 = self.prepared_id("S-1001")
        self.assertNotEqual(rid1, rid2)
        self.assertEqual(self.request_row(rid2)["status"], "PREPARED")

        # Step 5: Approve and execute the new request
        self.decide(rid2, "approve", headers=APPROVER2)
        r2 = self.execute(rid2, headers=APPROVER2)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["data"]["status"], "VERIFIED")
        self.assertTrue(r2.get_json()["data"]["verified"])

        # Connector account is now truly DISABLED
        self.assertEqual(self.connector_status("Slack", "S-1001"), "DISABLED")

    def test_concurrent_execution_race_is_safe(self):
        """Racing execute calls on the same approved request: exactly one executes, neither corrupts."""
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")

        def call_exec():
            # Need a new test client per thread
            client = self.app.test_client()
            return client.post(f"/api/v1/deprovision-requests/{rid}/execute", headers=APPROVER)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(call_exec)
            f2 = ex.submit(call_exec)
            r1, r2 = f1.result(), f2.result()

        # Both requests get 200 (one executed, one got idempotent replay or both safely serialized)
        # or one got 200 and one got 409 if in the middle of executing
        statuses = [r1.status_code, r2.status_code]
        self.assertIn(200, statuses)

        # The request is now VERIFIED
        self.assertEqual(self.request_row(rid)["status"], "VERIFIED")
        self.assertEqual(self.connector_status("Slack", "S-1001"), "DISABLED")
