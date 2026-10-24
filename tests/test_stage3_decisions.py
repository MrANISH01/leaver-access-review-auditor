"""Stage 3: approve / reject, authorization, separation of duties, state machine, idempotency, audit."""
import dataclasses
import unittest

from app import create_app
from tests.base import (APPROVER, APPROVER2, OUTSIDER, PREPARER, RequestTestCase, install_spy)


class ApprovalTests(RequestTestCase):
    def test_authorized_approver_can_approve(self):
        rid = self.prepared_id("S-1001")
        r = self.decide(rid, "approve", note="Confirmed with HR")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d["meta"], {"idempotent_replay": False})
        data = d["data"]
        self.assertEqual((data["status"], data["decided_by"], data["decision_note"]),
                         ("APPROVED", APPROVER["X-Actor"], "Confirmed with HR"))
        self.assertIsNotNone(data["decided_at"])
        self.assertFalse(data["verified"])        # approval is not verification
        self.assertIsNone(data["executed_at"])

    def test_approval_does_not_disable_anything_and_nothing_can_execute_yet(self):
        spy = install_spy(self)
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve")
        self.assertEqual(spy.disable_calls, [])
        self.assertEqual(self.connector_status("Slack", "S-1001"), "ACTIVE")
        r = self.client.post(f"/api/v1/deprovision-requests/{rid}/verify", headers=APPROVER)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.request_row(rid)["status"], "APPROVED")

    def test_approval_is_audited_with_actor_and_transition(self):
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve", note="ok")
        (row,) = self.audit("DEPROVISION_APPROVED")
        self.assertEqual((row["actor"], row["entity_type"], row["entity_id"]),
                         (APPROVER["X-Actor"], "deprovision_request", str(rid)))
        for text in ('"from": "PREPARED"', '"to": "APPROVED"', '"note": "ok"', PREPARER["X-Actor"]):
            self.assertIn(text, row["detail_json"])

    def test_approve_without_a_body_works(self):
        self.assertEqual(self.decide(self.prepared_id(), "approve").status_code, 200)

    def test_approver_allowlist_is_case_insensitive(self):
        rid = self.prepared_id()
        r = self.decide(rid, "approve", headers={"X-Actor": "APPROVER@Acme.Example"})
        self.assertEqual(r.status_code, 200)

    def test_one_approver_can_approve_a_request_prepared_by_another_approver(self):
        rid = self.prepared_id("S-1001", headers=APPROVER)
        self.assertEqual(self.decide(rid, "approve", headers=APPROVER2).status_code, 200)

    # ---- authorization ----
    def test_actor_not_on_allowlist_cannot_approve(self):
        rid = self.prepared_id()
        r = self.decide(rid, "approve", headers=OUTSIDER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (403, "APPROVER_NOT_AUTHORIZED"))
        row = self.request_row(rid)
        self.assertEqual((row["status"], row["decided_by"]), ("PREPARED", None))
        (denied,) = self.audit("DEPROVISION_APPROVE_DENIED")
        self.assertEqual((denied["actor"], denied["entity_id"]), (OUTSIDER["X-Actor"], str(rid)))
        self.assertIn("UNAUTHORIZED_APPROVER", denied["detail_json"])

    def test_preparer_who_is_not_an_approver_cannot_approve_their_own_request(self):
        rid = self.prepared_id(headers=PREPARER)
        r = self.decide(rid, "approve", headers=PREPARER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (403, "APPROVER_NOT_AUTHORIZED"))

    def test_nobody_can_approve_when_no_approvers_are_configured(self):
        rid = self.prepared_id()
        closed = create_app(dataclasses.replace(self.config, approver_actors=()))
        for headers in (APPROVER, PREPARER, OUTSIDER):
            r = self.decide(rid, "approve", headers=headers, client=closed.test_client())
            self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (403, "APPROVER_NOT_AUTHORIZED"))
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")
        reasons = " ".join(row["detail_json"] for row in self.audit("DEPROVISION_APPROVE_DENIED"))
        self.assertIn("NO_APPROVERS_CONFIGURED", reasons)

    def test_unauthorized_attempts_do_not_reveal_whether_a_request_exists(self):
        real = self.prepared_id()
        a = self.decide(real, "approve", headers=OUTSIDER).get_json()["error"]["code"]
        b = self.decide(9999, "approve", headers=OUTSIDER).get_json()["error"]["code"]
        self.assertEqual(a, b)

    # ---- separation of duties ----
    def test_self_approval_is_forbidden_even_for_an_allowlisted_approver(self):
        rid = self.prepared_id(headers=APPROVER)
        r = self.decide(rid, "approve", headers=APPROVER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (403, "SELF_APPROVAL_FORBIDDEN"))
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")
        (denied,) = self.audit("DEPROVISION_APPROVE_DENIED")
        self.assertIn("SELF_APPROVAL", denied["detail_json"])
        self.assertEqual(denied["actor"], APPROVER["X-Actor"])

    def test_self_approval_cannot_be_bypassed_by_changing_the_case_of_the_actor(self):
        rid = self.prepared_id(headers=APPROVER)
        for variant in ("APPROVER@ACME.EXAMPLE", "Approver@Acme.Example"):
            r = self.decide(rid, "approve", headers={"X-Actor": variant})
            self.assertEqual(r.get_json()["error"]["code"], "SELF_APPROVAL_FORBIDDEN", variant)
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")

    def test_a_preparer_may_withdraw_their_own_request_by_rejecting_it(self):
        rid = self.prepared_id(headers=APPROVER)
        self.assertEqual(self.decide(rid, "reject", headers=APPROVER, note="Prepared by mistake").status_code, 200)
        self.assertEqual(self.request_row(rid)["status"], "REJECTED")

    # ---- rejection ----
    def test_reject_records_decision_and_note(self):
        rid = self.prepared_id()
        r = self.decide(rid, "reject", note="Still on notice period")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]
        self.assertEqual((data["status"], data["decided_by"], data["decision_note"]),
                         ("REJECTED", APPROVER["X-Actor"], "Still on notice period"))
        (row,) = self.audit("DEPROVISION_REJECTED")
        self.assertEqual((row["actor"], row["entity_id"]), (APPROVER["X-Actor"], str(rid)))
        self.assertIn("Still on notice period", row["detail_json"])

    def test_reject_does_not_touch_the_account(self):
        spy = install_spy(self)
        self.decide(self.prepared_id(), "reject")
        self.assertEqual(spy.disable_calls, [])
        self.assertEqual(self.connector_status("Slack", "S-1001"), "ACTIVE")

    def test_actor_not_on_allowlist_cannot_reject(self):
        rid = self.prepared_id()
        r = self.decide(rid, "reject", headers=OUTSIDER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (403, "APPROVER_NOT_AUTHORIZED"))
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")
        self.assertEqual(len(self.audit("DEPROVISION_REJECT_DENIED")), 1)

    # ---- invalid transitions ----
    def test_cannot_approve_a_rejected_request(self):
        rid = self.prepared_id()
        self.decide(rid, "reject")
        r = self.decide(rid, "approve", headers=APPROVER2)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "INVALID_STATE"))
        self.assertEqual(r.get_json()["error"]["details"]["current_status"], "REJECTED")
        self.assertEqual(self.request_row(rid)["status"], "REJECTED")

    def test_cannot_reject_an_approved_request(self):
        rid = self.prepared_id()
        self.decide(rid, "approve")
        r = self.decide(rid, "reject", headers=APPROVER2)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "INVALID_STATE"))
        self.assertEqual(self.request_row(rid)["status"], "APPROVED")

    def test_a_second_approver_cannot_re_approve_or_overwrite_the_first_decision(self):
        rid = self.prepared_id()
        self.decide(rid, "approve", headers=APPROVER)
        r = self.decide(rid, "approve", headers=APPROVER2)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "INVALID_STATE"))
        self.assertEqual(self.request_row(rid)["decided_by"], APPROVER["X-Actor"])
        self.assertEqual(len(self.audit("DEPROVISION_APPROVED")), 1)
        self.assertEqual(len(self.audit("DEPROVISION_APPROVE_DENIED")), 1)

    def test_decision_on_unknown_request_is_404_and_audited(self):
        r = self.decide(9999, "approve", headers=APPROVER)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (404, "NOT_FOUND"))
        (row,) = self.audit("DEPROVISION_APPROVE_DENIED")
        self.assertEqual((row["entity_id"], row["actor"]), ("9999", APPROVER["X-Actor"]))

    # ---- idempotency ----
    def test_repeating_the_same_approval_is_an_idempotent_replay(self):
        rid = self.prepared_id()
        first = self.decide(rid, "approve", note="first").get_json()["data"]
        again = self.decide(rid, "approve", note="a different note")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.get_json()["meta"], {"idempotent_replay": True})
        data = again.get_json()["data"]
        self.assertEqual((data["decided_at"], data["decision_note"]), (first["decided_at"], "first"))   # unchanged
        self.assertEqual(len(self.audit("DEPROVISION_APPROVED")), 1)                                   # no second approval
        self.assertEqual(len(self.audit("DEPROVISION_DECISION_REPLAYED")), 1)

    def test_repeating_the_same_rejection_is_an_idempotent_replay(self):
        rid = self.prepared_id()
        self.decide(rid, "reject")
        again = self.decide(rid, "reject")
        self.assertEqual((again.status_code, again.get_json()["meta"]["idempotent_replay"]), (200, True))
        self.assertEqual(len(self.audit("DEPROVISION_REJECTED")), 1)

    # ---- validation ----
    def test_decisions_require_an_actor(self):
        rid = self.prepared_id()
        for action in ("approve", "reject"):
            r = self.client.post(f"/api/v1/deprovision-requests/{rid}/{action}")
            self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (400, "ACTOR_REQUIRED"))

    def test_bad_notes_are_rejected_without_changing_state(self):
        rid = self.prepared_id()
        for body in ({"note": "x" * 501}, {"note": 123}, {"note": ["a"]}):
            r = self.client.post(f"/api/v1/deprovision-requests/{rid}/approve", headers=APPROVER, json=body)
            self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (422, "VALIDATION_ERROR"))
        r = self.client.post(f"/api/v1/deprovision-requests/{rid}/approve", headers=APPROVER, data="not json")
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (400, "INVALID_JSON"))
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")

    # ---- audit trail as a whole ----
    def test_full_story_is_in_the_audit_trail_in_order(self):
        rid = self.prepared_id("S-1001")                    # PREPARED
        self.decide(rid, "approve", headers=OUTSIDER)       # denied: not an approver
        self.decide(self.prepared_id("G-2001", headers=APPROVER), "approve", headers=APPROVER)  # denied: self-approval
        self.decide(rid, "approve", headers=APPROVER)       # APPROVED
        self.decide(rid, "approve", headers=APPROVER)       # replay
        self.decide(rid, "reject", headers=APPROVER2)       # denied: invalid state
        events = [r["event"] for r in self.audit(entity_type="deprovision_request")]
        self.assertEqual(events, ["DEPROVISION_PREPARED", "DEPROVISION_APPROVE_DENIED", "DEPROVISION_PREPARED",
                                  "DEPROVISION_APPROVE_DENIED", "DEPROVISION_APPROVED",
                                  "DEPROVISION_DECISION_REPLAYED", "DEPROVISION_REJECT_DENIED"])

    def test_the_connector_is_never_called_across_the_whole_workflow(self):
        spy = install_spy(self)
        rid = self.prepared_id("S-1001")
        self.decide(rid, "approve", headers=OUTSIDER)
        self.decide(rid, "approve")
        other = self.prepared_id("G-2001")
        self.decide(other, "reject")
        self.assertEqual(spy.disable_calls, [])
        self.assertTrue(all(a.status.value == "ACTIVE" for a in spy.list_accounts()
                            if a.external_account_id in ("S-1001", "G-2001")))


if __name__ == "__main__":
    unittest.main()
