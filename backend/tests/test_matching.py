"""Pure unit tests for identity matching (no DB, no Flask)."""
import unittest

from app.models import (AccountStatus, AccountType, Employee, EmploymentStatus, MatchConfidence,
                        MatchMethod, SaaSAccount)
from app.services.matching import EmployeeIndex, match_account


def employee(eid, name, email, status=EmploymentStatus.TERMINATED):
    return Employee(eid, name, email, status, "2026-09-01" if status is EmploymentStatus.TERMINATED else None)


def account(email, name, employee_id=None):
    return SaaSAccount("Slack", "S-1", email, name, "u", AccountType.INDIVIDUAL, AccountStatus.ACTIVE,
                       None, employee_id)


PRIYA = employee("E102", "Priya Nair", "priya.sharma@acme.example")


class MatchingTests(unittest.TestCase):
    def match(self, acct, *employees):
        return match_account(acct, EmployeeIndex(employees))

    def test_work_email_match_is_high_confidence(self):
        m = self.match(account("priya.sharma@acme.example", "Priya Nair"), PRIYA)
        self.assertEqual((m.employee, m.method, m.confidence, m.needs_review),
                         (PRIYA, MatchMethod.WORK_EMAIL, MatchConfidence.HIGH, False))

    def test_tc2_surname_change_still_matches_on_email(self):
        m = self.match(account("priya.sharma@acme.example", "Priya Sharma"), PRIYA)
        self.assertEqual(m.employee.employee_id, "E102")
        self.assertEqual(m.method, MatchMethod.WORK_EMAIL)
        self.assertTrue(m.rationale["name_differs"])
        self.assertIn("Last name differs", m.note)
        self.assertIn("Sharma", m.note)
        self.assertIn("Nair", m.note)

    def test_email_match_is_case_and_whitespace_insensitive(self):
        m = self.match(account("  Priya.Sharma@ACME.example ", "Priya Sharma"), PRIYA)
        self.assertEqual(m.method, MatchMethod.WORK_EMAIL)

    def test_name_alone_would_not_have_matched_tc2(self):
        # No email link: 'Priya Sharma' != 'Priya Nair', so a name-based matcher finds nothing.
        m = self.match(account("someone@personal.example", "Priya Sharma"), PRIYA)
        self.assertIsNone(m.employee)

    def test_employee_id_match_is_high_confidence(self):
        m = self.match(account("m.i@contractor.example", "M. Iyer", employee_id="E106"),
                       employee("E106", "Meera Iyer", "meera.iyer@acme.example"))
        self.assertEqual((m.method, m.confidence), (MatchMethod.EMPLOYEE_ID, MatchConfidence.HIGH))

    def test_email_and_employee_id_agreeing_is_corroborated(self):
        m = self.match(account("priya.sharma@acme.example", "Priya Sharma", employee_id="E102"), PRIYA)
        self.assertEqual(m.method, MatchMethod.WORK_EMAIL)
        self.assertTrue(m.rationale["employee_id_corroborates"])

    def test_conflicting_email_and_employee_id_needs_review(self):
        other = employee("E999", "Other Person", "other@acme.example")
        m = self.match(account("priya.sharma@acme.example", "Priya Sharma", employee_id="E999"), PRIYA, other)
        self.assertTrue(m.needs_review)
        self.assertIsNone(m.employee)
        self.assertIsNone(m.confidence)
        self.assertEqual(sorted(m.rationale["candidates"]), ["E102", "E999"])

    def test_duplicate_hr_email_is_ambiguous(self):
        twin = employee("E200", "Priya Twin", "priya.sharma@acme.example")
        m = self.match(account("priya.sharma@acme.example", "Priya Sharma"), PRIYA, twin)
        self.assertTrue(m.needs_review)
        self.assertIsNone(m.employee)

    def test_name_only_is_low_confidence_and_needs_review(self):
        karan = employee("E105", "Karan Singh", "karan.singh@acme.example")
        m = self.match(account("karan.personal@mailbox.example", "  karan   SINGH "), karan)
        self.assertEqual((m.method, m.confidence, m.needs_review), (MatchMethod.NAME_ONLY, MatchConfidence.LOW, True))
        self.assertEqual(m.employee, karan)   # linked for the reviewer's context only

    def test_ambiguous_name_links_nobody(self):
        a, b = employee("E1", "Sam Lee", "a@x"), employee("E2", "Sam Lee", "b@x")
        m = self.match(account("sam@personal.example", "Sam Lee"), a, b)
        self.assertTrue(m.needs_review)
        self.assertIsNone(m.employee)

    def test_no_match(self):
        m = self.match(account("stranger@x.example", "Totally Unknown"), PRIYA)
        self.assertEqual((m.employee, m.method, m.needs_review), (None, None, False))

    def test_missing_display_name_does_not_crash_or_claim_difference(self):
        m = self.match(account("priya.sharma@acme.example", None), PRIYA)
        self.assertEqual(m.method, MatchMethod.WORK_EMAIL)
        self.assertIsNone(m.rationale["name_differs"])


if __name__ == "__main__":
    unittest.main()
