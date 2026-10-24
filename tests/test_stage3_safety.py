"""Stage 3: state machine, DB-level guards, concurrency, audit-log endpoint, whoami, config."""
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.config import Config, ConfigError
from app.db import init_db
from app.models import ALLOWED_TRANSITIONS, RequestStatus, can_transition
from tests.base import (APPROVER, APPROVER2, OUTSIDER, PREPARER, AppTestCase, RequestTestCase)


class StateMachineTests(unittest.TestCase):
    def test_every_status_has_a_transition_entry(self):
        self.assertEqual(set(ALLOWED_TRANSITIONS), set(RequestStatus))

    def test_only_approved_can_become_executing(self):
        sources = {s for s, targets in ALLOWED_TRANSITIONS.items() if RequestStatus.EXECUTING in targets}
        self.assertEqual(sources, {RequestStatus.APPROVED})

    def test_decisions_come_only_from_prepared(self):
        self.assertEqual(ALLOWED_TRANSITIONS[RequestStatus.PREPARED],
                         {RequestStatus.APPROVED, RequestStatus.REJECTED})
        for status in RequestStatus:
            if status is not RequestStatus.PREPARED:
                self.assertFalse(can_transition(status.value, "APPROVED"), status)
                self.assertFalse(can_transition(status.value, "REJECTED"), status)

    def test_terminal_states_have_no_exits(self):
        for status in ("REJECTED", "EXECUTION_FAILED", "VERIFIED", "VERIFICATION_FAILED"):
            self.assertEqual(ALLOWED_TRANSITIONS[RequestStatus(status)], frozenset(), status)

    def test_verified_is_only_reachable_from_executed_unverified(self):
        sources = {s for s, targets in ALLOWED_TRANSITIONS.items() if RequestStatus.VERIFIED in targets}
        self.assertEqual(sources, {RequestStatus.EXECUTED_UNVERIFIED})

    def test_garbage_is_never_allowed(self):
        self.assertFalse(can_transition("NOPE", "APPROVED"))
        self.assertFalse(can_transition("PREPARED", "NOPE"))


class DbGuardTests(RequestTestCase):
    def test_enum_matches_schema_check_constraint(self):
        db = self.raw_db()
        for status in RequestStatus:
            db.execute("INSERT INTO deprovision_requests (finding_id, system, external_account_id, status, "
                       "idempotency_key, prepared_by, prepared_at) VALUES (?,?,?,?,?,?,?)",
                       (self.finding_id("J-3005"), "Jira", "J-3005", status.value, f"k-{status.value}", "a", "t"))
            db.rollback()   # keep the unique indexes out of the way
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO deprovision_requests (finding_id, system, external_account_id, status, "
                       "idempotency_key, prepared_by, prepared_at) VALUES (1,'Slack','S-1','BOGUS','k','a','t')")

    def test_trigger_blocks_self_approval_even_if_application_code_is_bypassed(self):
        rid = self.prepared_id(headers=APPROVER)
        db = self.raw_db()
        for decided_by in ("approver@acme.example", "APPROVER@acme.example", None):
            with self.subTest(decided_by=decided_by), self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE deprovision_requests SET status='APPROVED', decided_by=? WHERE id=?",
                           (decided_by, rid))
        db.rollback()
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")

    def test_trigger_allows_a_different_approver_and_a_self_rejection(self):
        rid = self.prepared_id(headers=APPROVER)
        db = self.raw_db()
        db.execute("UPDATE deprovision_requests SET status='REJECTED', decided_by='approver@acme.example' WHERE id=?",
                   (rid,))
        db.commit()
        rid2 = self.prepared_id("G-2001", headers=APPROVER)
        db.execute("UPDATE deprovision_requests SET status='APPROVED', decided_by='approver2@acme.example' "
                   "WHERE id=?", (rid2,))
        db.commit()

    def test_trigger_also_guards_later_states(self):
        rid = self.prepared_id(headers=APPROVER)
        db = self.raw_db()
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE deprovision_requests SET status='EXECUTING' WHERE id=?", (rid,))   # no approver at all

    def test_database_allows_one_open_request_per_account_across_findings(self):
        self.prepared_id("S-1001")
        self.run_scan()
        newer = self.findings_by_account()["S-1001"]["id"]
        db = self.raw_db()
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO deprovision_requests (finding_id, system, external_account_id, status, "
                       "idempotency_key, prepared_by, prepared_at) VALUES (?, 'Slack','S-1001','PREPARED','k2','a','t')",
                       (newer,))

    def test_existing_database_is_upgraded_in_place_without_losing_data(self):
        rid = self.prepared_id("S-1001")
        db = self.raw_db()
        db.execute("DROP INDEX one_open_request_per_account")
        db.execute("DROP TRIGGER deprovision_separation_of_duties")
        db.commit()
        init_db(self.db_path)   # what every startup does
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('index','trigger')")}
        self.assertTrue({"one_open_request_per_account", "deprovision_separation_of_duties"} <= names)
        self.assertEqual(self.request_row(rid)["status"], "PREPARED")   # data survived

    def test_audit_log_stays_append_only_after_decisions(self):
        rid = self.prepared_id()
        self.decide(rid, "approve")
        db = self.raw_db()
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("DELETE FROM audit_log WHERE event='DEPROVISION_APPROVED'")


class ConcurrencyTests(RequestTestCase):
    def race(self, calls):
        barrier = threading.Barrier(len(calls))

        def run(call):
            client = self.app.test_client()
            barrier.wait()
            return call(client)

        with ThreadPoolExecutor(len(calls)) as ex:
            return list(ex.map(run, calls))

    def test_two_approvers_racing_produce_exactly_one_approval(self):
        for account in ("S-1001", "G-2001", "J-3001", "S-1002", "G-2002"):
            with self.subTest(account=account):
                rid = self.prepared_id(account)
                results = self.race([lambda c: self.decide(rid, "approve", APPROVER, client=c),
                                     lambda c: self.decide(rid, "approve", APPROVER2, client=c)])
                self.assertEqual(sorted(r.status_code for r in results), [200, 409])
                self.assertEqual(self.request_row(rid)["status"], "APPROVED")
                approvals = [a for a in self.audit("DEPROVISION_APPROVED") if a["entity_id"] == str(rid)]
                self.assertEqual(len(approvals), 1)
                self.assertEqual(self.request_row(rid)["decided_by"], approvals[0]["actor"])

    def test_the_same_approver_double_submitting_is_safe(self):
        for account in ("S-1001", "G-2001", "J-3001"):
            with self.subTest(account=account):
                rid = self.prepared_id(account)
                results = self.race([lambda c: self.decide(rid, "approve", APPROVER, client=c)] * 2)
                self.assertEqual([r.status_code for r in results], [200, 200])
                self.assertEqual(sorted(r.get_json()["meta"]["idempotent_replay"] for r in results), [False, True])
                self.assertEqual(len([a for a in self.audit("DEPROVISION_APPROVED") if a["entity_id"] == str(rid)]), 1)

    def test_approve_and_reject_racing_leave_one_consistent_outcome(self):
        for account in ("S-1001", "G-2001", "J-3001"):
            with self.subTest(account=account):
                rid = self.prepared_id(account)
                results = self.race([lambda c: self.decide(rid, "approve", APPROVER, client=c),
                                     lambda c: self.decide(rid, "reject", APPROVER2, client=c)])
                self.assertEqual(sorted(r.status_code for r in results), [200, 409])
                final = self.request_row(rid)["status"]
                self.assertIn(final, ("APPROVED", "REJECTED"))
                decisions = [a for a in self.audit() if a["entity_id"] == str(rid)
                             and a["event"] in ("DEPROVISION_APPROVED", "DEPROVISION_REJECTED")]
                self.assertEqual(len(decisions), 1)
                self.assertEqual(decisions[0]["event"], f"DEPROVISION_{final}")


class AuditLogEndpointTests(RequestTestCase):
    def test_lists_events_oldest_first_with_parsed_detail(self):
        rid = self.prepared_id()
        self.decide(rid, "approve", headers=OUTSIDER)
        self.decide(rid, "approve")
        body = self.client.get("/api/v1/audit-log").get_json()
        events = [e["event"] for e in body["data"]]
        self.assertEqual(events[-3:], ["DEPROVISION_PREPARED", "DEPROVISION_APPROVE_DENIED", "DEPROVISION_APPROVED"])
        self.assertEqual(body["meta"]["count"], len(body["data"]))
        denied = [e for e in body["data"] if e["event"] == "DEPROVISION_APPROVE_DENIED"][0]
        self.assertEqual(denied["actor"], OUTSIDER["X-Actor"])
        self.assertEqual(denied["detail"]["reason"], "UNAUTHORIZED_APPROVER")
        self.assertEqual(set(denied), {"id", "ts", "actor", "event", "entity_type", "entity_id", "detail"})

    def test_filters(self):
        rid = self.prepared_id()
        self.decide(rid, "approve")
        for_request = self.client.get(f"/api/v1/audit-log?entity_type=deprovision_request&entity_id={rid}").get_json()["data"]
        self.assertEqual([e["event"] for e in for_request], ["DEPROVISION_PREPARED", "DEPROVISION_APPROVED"])
        scans = self.client.get("/api/v1/audit-log?entity_type=scan").get_json()["data"]
        self.assertTrue(scans and all(e["entity_type"] == "scan" for e in scans))
        only = self.client.get("/api/v1/audit-log?event=DEPROVISION_APPROVED").get_json()["data"]
        self.assertEqual(len(only), 1)

    def test_limit_returns_the_most_recent_events_in_order(self):
        rid = self.prepared_id()
        self.decide(rid, "approve")
        last_two = self.client.get("/api/v1/audit-log?limit=2").get_json()["data"]
        self.assertEqual([e["event"] for e in last_two], ["DEPROVISION_PREPARED", "DEPROVISION_APPROVED"])

    def test_limit_validation(self):
        for bad in ("0", "501", "abc", "-1"):
            r = self.client.get(f"/api/v1/audit-log?limit={bad}")
            self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (422, "VALIDATION_ERROR"), bad)

    def test_audit_log_has_no_write_endpoints(self):
        for method in ("post", "put", "delete", "patch"):
            r = getattr(self.client, method)("/api/v1/audit-log", headers=APPROVER)
            self.assertEqual(r.status_code, 405, method)


class WhoAmITests(AppTestCase):
    def test_requires_actor(self):
        self.assertEqual(self.client.get("/api/v1/whoami").status_code, 400)

    def test_reports_whether_the_actor_may_approve(self):
        for headers, expected in ((APPROVER, True), (APPROVER2, True), (PREPARER, False), (OUTSIDER, False),
                                  ({"X-Actor": "APPROVER@ACME.EXAMPLE"}, True)):
            data = self.client.get("/api/v1/whoami", headers=headers).get_json()["data"]
            self.assertEqual(data, {"actor": headers["X-Actor"], "can_approve": expected})

    def test_health_reports_whether_approvers_are_configured_without_listing_them(self):
        data = self.client.get("/api/v1/health").get_json()["data"]
        self.assertTrue(data["approvers_configured"])
        self.assertNotIn("approver@acme.example", str(data))


class ApproverConfigTests(unittest.TestCase):
    def test_default_is_empty_so_nobody_can_approve(self):
        cfg = Config.from_env({})
        self.assertEqual(cfg.approver_actors, ())
        self.assertFalse(cfg.is_approver("approver@acme.example"))

    def test_parsing_normalises_and_dedupes(self):
        cfg = Config.from_env({"APPROVER_ACTORS": " Approver@Acme.example, approver2@acme.example ,approver@ACME.example,"})
        self.assertEqual(cfg.approver_actors, ("approver@acme.example", "approver2@acme.example"))
        cfg.validate()

    def test_wildcards_and_junk_are_rejected(self):
        for bad in ("*", "a@x.com, *", "bad actor", "x;y", "a@x.com/b"):
            with self.subTest(value=bad), self.assertRaises(ConfigError):
                Config.from_env({"APPROVER_ACTORS": bad}).validate()

    def test_membership_is_exact_not_substring(self):
        cfg = Config(approver_actors=("approver@acme.example",))
        for other in ("approver@acme.example.evil.com", "xapprover@acme.example", "approver@acme", ""):
            self.assertFalse(cfg.is_approver(other), other)


if __name__ == "__main__":
    unittest.main()
