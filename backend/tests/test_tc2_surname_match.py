"""TC2: Match an employee whose surname changed using their verified work email."""
import unittest

from tests.base import AppTestCase, acct, emp


class TC2SurnameChangeTests(AppTestCase):
    def test_priya_is_matched_by_work_email_despite_surname_change(self):
        self.run_scan()
        by_account = self.findings_by_account()
        for account_id in ("S-1002", "G-2002", "J-3002"):
            with self.subTest(account=account_id):
                f = by_account[account_id]
                self.assertEqual(f["account"]["display_name"], "Priya Sharma")   # old surname on the SaaS side
                self.assertEqual(f["employee"]["full_name"], "Priya Nair")        # new surname in HR
                self.assertEqual(f["employee"]["employee_id"], "E102")
                self.assertEqual((f["match_method"], f["match_confidence"]), ("WORK_EMAIL", "HIGH"))
                self.assertEqual(f["classification"], "LEAVER_ACTIVE")
                self.assertTrue(f["deprovision_eligible"])

    def test_evidence_explains_the_name_difference(self):
        self.run_scan()
        f = self.findings_by_account()["S-1002"]
        (why,) = self.evidence_of(f, "MATCH_RATIONALE")
        self.assertEqual(why["method"], "WORK_EMAIL")
        self.assertTrue(why["name_differs"])
        self.assertEqual((why["account_email"], why["hr_work_email"]),
                         ("priya.sharma@acme.example", "priya.sharma@acme.example"))
        for text in ("Sharma", "Nair", "work email"):
            self.assertIn(text, why["note"])
        self.assertEqual(f["account"]["last_login_at"], "2026-09-28T09:14:00Z")

    def test_email_match_ignores_case(self):
        self.use_data(
            employees=[emp("E1", "Priya Nair", "priya.sharma@acme.example")],
            accounts=[acct("S-1", "PRIYA.Sharma@Acme.Example", "Priya Sharma")])
        self.run_scan()
        f = self.findings_by_account()["S-1"]
        self.assertEqual((f["classification"], f["match_method"]), ("LEAVER_ACTIVE", "WORK_EMAIL"))

    def test_without_a_verified_email_a_new_surname_is_never_guessed(self):
        # Account email is personal and the surname differs: no match by name, so no leaver flag.
        self.use_data(
            employees=[emp("E1", "Priya Nair", "priya.sharma@acme.example")],
            accounts=[acct("S-1", "priya.personal@mail.example", "Priya Sharma")])
        self.run_scan()
        f = self.findings_by_account()["S-1"]
        self.assertEqual(f["classification"], "NO_MATCH")
        self.assertIsNone(f["employee"])
        self.assertFalse(f["deprovision_eligible"])

    def test_name_only_match_is_needs_review_and_not_eligible(self):
        self.run_scan()
        karan = self.findings_by_account()["G-2005"]
        self.assertEqual(karan["classification"], "NEEDS_REVIEW")
        self.assertEqual((karan["match_method"], karan["match_confidence"]), ("NAME_ONLY", "LOW"))
        self.assertEqual(karan["employee"]["employee_id"], "E105")   # shown for the reviewer
        self.assertFalse(karan["deprovision_eligible"])
        self.assertIn("reviewer must confirm", karan["reason"])

    def test_conflicting_identity_signals_need_review(self):
        self.use_data(
            employees=[emp("E1", "Priya Nair", "priya.sharma@acme.example"), emp("E2", "Other", "other@acme.example")],
            accounts=[acct("S-1", "priya.sharma@acme.example", "Priya Sharma", employee_id="E2")])
        self.run_scan()
        f = self.findings_by_account()["S-1"]
        self.assertEqual(f["classification"], "NEEDS_REVIEW")
        self.assertIsNone(f["employee"])
        self.assertFalse(f["deprovision_eligible"])


if __name__ == "__main__":
    unittest.main()
