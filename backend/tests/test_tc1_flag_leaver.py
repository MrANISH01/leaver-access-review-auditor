"""TC1: Flag a former employee's active account and show last login when available."""
import unittest

from tests.base import AppTestCase


class TC1FlagLeaverTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.run_scan()
        self.by_account = self.findings_by_account()

    def test_rahul_active_accounts_flagged_in_all_three_systems(self):
        for account_id in ("S-1001", "G-2001", "J-3001"):
            with self.subTest(account=account_id):
                f = self.by_account[account_id]
                self.assertEqual(f["classification"], "LEAVER_ACTIVE")
                self.assertEqual(f["match_method"], "WORK_EMAIL")
                self.assertEqual(f["match_confidence"], "HIGH")
                self.assertEqual(f["employee"]["employee_id"], "E101")
                self.assertEqual(f["employee"]["employment_status"], "TERMINATED")
                self.assertEqual(f["account"]["status"], "ACTIVE")
                self.assertEqual(f["reason"], "Employee terminated 2026-09-15 but account is still ACTIVE")
                self.assertTrue(f["deprovision_eligible"])

    def test_last_login_is_shown_when_available(self):
        f = self.by_account["S-1001"]
        self.assertEqual(f["account"]["last_login_at"], "2026-09-14T17:42:00Z")
        (login,) = self.evidence_of(f, "LAST_LOGIN")
        self.assertEqual(login, {"last_login_at": "2026-09-14T17:42:00Z", "available": True,
                                 "after_termination": False})

    def test_last_login_is_null_not_guessed_when_unavailable(self):
        f = self.by_account["J-3001"]
        self.assertEqual(f["classification"], "LEAVER_ACTIVE")   # still flagged without a login time
        self.assertIsNone(f["account"]["last_login_at"])
        (login,) = self.evidence_of(f, "LAST_LOGIN")
        self.assertEqual(login, {"last_login_at": None, "available": False, "after_termination": None})

    def test_evidence_records_hr_and_account_facts(self):
        f = self.by_account["G-2001"]
        (hr,) = self.evidence_of(f, "HR_RECORD")
        self.assertEqual((hr["employee_id"], hr["termination_date"]), ("E101", "2026-09-15"))
        (acc,) = self.evidence_of(f, "ACCOUNT_RECORD")
        self.assertEqual((acc["system"], acc["external_account_id"], acc["status"]), ("GitHub", "G-2001", "ACTIVE"))

    def test_active_employees_and_already_disabled_accounts_are_not_flagged(self):
        for account_id in ("S-1003", "G-2003", "J-3004"):   # Arjun, active employee
            self.assertEqual(self.by_account[account_id]["classification"], "OK")
        neha = self.by_account["S-1004"]                     # terminated, but account already DISABLED
        self.assertEqual(neha["classification"], "OK")
        self.assertIn("already DISABLED", neha["reason"])
        self.assertFalse(neha["deprovision_eligible"])

    def test_exact_set_of_flagged_leavers(self):
        flagged = {a for a, f in self.by_account.items() if f["classification"] == "LEAVER_ACTIVE"}
        self.assertEqual(flagged, {"S-1001", "G-2001", "J-3001",    # Rahul
                                   "S-1002", "G-2002", "J-3002",    # Priya (TC2)
                                   "J-3005"})                        # Meera (matched by employee_id)

    def test_scan_summary_counts(self):
        scan = self.client.get("/api/v1/scans/1").get_json()["data"]
        self.assertEqual(scan["status"], "COMPLETED")
        self.assertEqual(scan["summary"]["total_accounts"], 16)
        self.assertEqual(scan["summary"]["by_classification"],
                         {"LEAVER_ACTIVE": 7, "EXCLUDED": 4, "NEEDS_REVIEW": 1, "NO_MATCH": 0, "OK": 4})


if __name__ == "__main__":
    unittest.main()
