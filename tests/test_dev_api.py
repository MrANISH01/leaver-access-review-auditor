import json
import unittest

from tests.base import ACTOR, AppTestCase


class DevDisabledTests(AppTestCase):
    demo_mode = False

    def test_dev_endpoints_do_not_exist_without_demo_mode(self):
        for method, path in (("post", "/reset"), ("get", "/connector/accounts"),
                             ("post", "/fault-injection"), ("delete", "/fault-injection")):
            with self.subTest(path=path):
                r = getattr(self.client, method)(f"/api/v1/dev{path}", headers=ACTOR)
                self.assertEqual(r.status_code, 404)


class DevResetTests(AppTestCase):
    demo_mode = True

    def test_reset_requires_actor(self):
        r = self.client.post("/api/v1/dev/reset")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "ACTOR_REQUIRED")

    def test_reset_rejects_malformed_actor(self):
        r = self.client.post("/api/v1/dev/reset", headers={"X-Actor": "bad actor; DROP"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "INVALID_ACTOR")

    def test_reset_seeds_db_and_audits(self):
        r = self.client.post("/api/v1/dev/reset", headers=ACTOR)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()["data"]
        self.assertEqual((data["employees_seeded"], data["exclusions_seeded"], data["connector_accounts"]), (6, 1, 16))
        db = self.raw_db()
        self.assertEqual(db.execute("SELECT COUNT(*) FROM employees").fetchone()[0], 6)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM exclusions").fetchone()[0], 1)
        row = db.execute("SELECT actor, event FROM audit_log").fetchone()
        self.assertEqual((row["actor"], row["event"]), (ACTOR["X-Actor"], "DEMO_RESET"))

    def test_reset_is_repeatable_without_duplicates(self):
        self.client.post("/api/v1/dev/reset", headers=ACTOR)
        self.client.post("/api/v1/dev/reset", headers=ACTOR)
        db = self.raw_db()
        self.assertEqual(db.execute("SELECT COUNT(*) FROM employees").fetchone()[0], 6)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0], 1)  # fresh trail

    def test_reset_restores_connector_state_and_clears_faults(self):
        self.connector.disable_account("Slack", "S-1001")
        self.client.post("/api/v1/dev/fault-injection", headers=ACTOR, json={"mode": "error"})
        self.client.post("/api/v1/dev/reset", headers=ACTOR)
        accounts = {a["external_account_id"]: a for a in
                    self.client.get("/api/v1/dev/connector/accounts").get_json()["data"]}
        self.assertEqual(accounts["S-1001"]["status"], "ACTIVE")
        self.assertEqual(self.client.get("/api/v1/dev/fault-injection").get_json()["data"]["default"], "none")


class FaultInjectionApiTests(AppTestCase):
    demo_mode = True

    def post(self, body, headers=ACTOR):
        return self.client.post("/api/v1/dev/fault-injection", headers=headers, json=body)

    def test_set_global_and_per_account_fault(self):
        self.assertEqual(self.post({"mode": "reject"}).get_json()["data"]["default"], "reject")
        data = self.post({"mode": "silent_noop", "system": "Slack", "external_account_id": "S-1001"}).get_json()["data"]
        self.assertEqual(data["per_account"], [{"system": "Slack", "external_account_id": "S-1001", "mode": "silent_noop"}])

    def test_fault_actually_reaches_connector(self):
        self.post({"mode": "silent_noop"})
        self.assertTrue(self.connector.disable_account("Slack", "S-1001").success)
        self.assertEqual(self.connector.get_account("Slack", "S-1001").status.value, "ACTIVE")

    def test_requires_actor(self):
        self.assertEqual(self.post({"mode": "error"}, headers={}).status_code, 400)

    def test_invalid_mode_is_422(self):
        r = self.post({"mode": "chaos"})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (422, "VALIDATION_ERROR"))

    def test_missing_body_is_400(self):
        r = self.client.post("/api/v1/dev/fault-injection", headers=ACTOR, data="not json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "INVALID_JSON")

    def test_half_specified_target_is_422(self):
        self.assertEqual(self.post({"mode": "error", "system": "Slack"}).status_code, 422)

    def test_unknown_account_is_404(self):
        r = self.post({"mode": "error", "system": "Slack", "external_account_id": "nope"})
        self.assertEqual(r.status_code, 404)

    def test_clear_and_audit(self):
        self.post({"mode": "error"})
        r = self.client.delete("/api/v1/dev/fault-injection", headers=ACTOR)
        self.assertEqual(r.get_json()["data"], {"default": "none", "per_account": []})
        events = [row["event"] for row in self.raw_db().execute("SELECT event FROM audit_log ORDER BY id")]
        self.assertEqual(events, ["FAULT_INJECTION_SET", "FAULT_INJECTION_CLEARED"])

    def test_connector_accounts_endpoint_is_ground_truth(self):
        self.connector.disable_account("Slack", "S-1001")
        data = self.client.get("/api/v1/dev/connector/accounts").get_json()["data"]
        self.assertEqual(len(data), 16)
        self.assertEqual(next(a for a in data if a["external_account_id"] == "S-1001")["status"], "DISABLED")
        json.dumps(data)  # serialisable


if __name__ == "__main__":
    unittest.main()
