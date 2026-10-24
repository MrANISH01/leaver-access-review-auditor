"""Unit tests for classification, eligibility and evidence building."""
import unittest

from app.models import (AccountStatus, AccountType, Classification, Employee, EmploymentStatus,
                        EvidenceType, MatchConfidence, SaaSAccount)
from app.services.classification import (build_evidence, classify, exclusion_rules,
                                         is_deprovision_eligible, last_login_evidence)
from app.services.matching import EmployeeIndex, match_account

LEAVER = Employee("E1", "Ravi Kumar", "ravi@acme.example", EmploymentStatus.TERMINATED, "2026-09-10")
STAFF = Employee("E2", "Asha Rao", "asha@acme.example", EmploymentStatus.ACTIVE)
INDEX = EmployeeIndex([LEAVER, STAFF])


def acct(email, name="x", atype=AccountType.INDIVIDUAL, status=AccountStatus.ACTIVE, login=None):
    return SaaSAccount("Slack", "S-1", email, name, "u", atype, status, login)


def run(account, exclusions=None):
    rules = exclusion_rules(account, exclusions or {})
    match = match_account(account, INDEX)
    return classify(account, match, rules), match, rules


class ClassifyTests(unittest.TestCase):
    def test_terminated_with_active_account_is_leaver_active(self):
        (c, reason), _, _ = run(acct("ravi@acme.example"))
        self.assertEqual(c, Classification.LEAVER_ACTIVE)
        self.assertIn("2026-09-10", reason)
        self.assertIn("still ACTIVE", reason)

    def test_terminated_with_disabled_account_is_ok(self):
        (c, reason), _, _ = run(acct("ravi@acme.example", status=AccountStatus.DISABLED))
        self.assertEqual(c, Classification.OK)
        self.assertIn("already DISABLED", reason)

    def test_active_employee_is_ok(self):
        (c, _), _, _ = run(acct("asha@acme.example"))
        self.assertEqual(c, Classification.OK)

    def test_no_match(self):
        (c, _), _, _ = run(acct("nobody@x.example", "Nobody"))
        self.assertEqual(c, Classification.NO_MATCH)

    def test_name_only_never_becomes_leaver_active(self):
        (c, _), match, _ = run(acct("ravi.private@mail.example", "Ravi Kumar"))
        self.assertEqual(c, Classification.NEEDS_REVIEW)
        self.assertEqual(match.confidence, MatchConfidence.LOW)

    def test_service_and_shared_accounts_are_excluded_even_if_email_matches_a_leaver(self):
        for atype in (AccountType.SERVICE, AccountType.SHARED):
            with self.subTest(atype=atype):
                (c, reason), _, rules = run(acct("ravi@acme.example", atype=atype))
                self.assertEqual(c, Classification.EXCLUDED)
                self.assertEqual(rules[0]["rule"], "ACCOUNT_TYPE")
                self.assertIn(atype.value.lower(), reason)

    def test_explicit_exclusion_row_excludes_individual_typed_account(self):
        ex = {("Slack", "S-1"): {"reason": "Shared mailbox", "added_by": "it", "added_at": "t"}}
        (c, reason), _, rules = run(acct("ravi@acme.example"), ex)
        self.assertEqual(c, Classification.EXCLUDED)
        self.assertEqual(rules[0]["rule"], "EXPLICIT_EXCLUSION")
        self.assertIn("Shared mailbox", reason)

    def test_no_guessing_from_names_like_admin(self):
        (c, _), _, rules = run(acct("admin@acme.example", "Admin"))
        self.assertEqual(rules, [])
        self.assertNotEqual(c, Classification.EXCLUDED)


class EligibilityTests(unittest.TestCase):
    def test_only_high_confidence_leaver_active_is_eligible(self):
        self.assertTrue(is_deprovision_eligible("LEAVER_ACTIVE", "HIGH"))
        self.assertFalse(is_deprovision_eligible("LEAVER_ACTIVE", "LOW"))
        self.assertFalse(is_deprovision_eligible("LEAVER_ACTIVE", None))
        for c in ("EXCLUDED", "NEEDS_REVIEW", "NO_MATCH", "OK"):
            self.assertFalse(is_deprovision_eligible(c, "HIGH"), c)


class EvidenceTests(unittest.TestCase):
    def types(self, evidence):
        return [t for t, _ in evidence]

    def test_leaver_evidence_set(self):
        account = acct("ravi@acme.example", login="2026-09-08T10:00:00Z")
        _, match, rules = run(account)
        ev = build_evidence(account, match, rules)
        self.assertEqual(self.types(ev), [EvidenceType.ACCOUNT_RECORD, EvidenceType.HR_RECORD,
                                          EvidenceType.MATCH_RATIONALE, EvidenceType.LAST_LOGIN])

    def test_excluded_evidence_has_rule_and_no_hr_link(self):
        account = acct("ravi@acme.example", atype=AccountType.SERVICE)
        _, match, rules = run(account)
        self.assertEqual(self.types(build_evidence(account, match, rules)),
                         [EvidenceType.ACCOUNT_RECORD, EvidenceType.EXCLUSION_RULE])

    def test_last_login_available_and_before_termination(self):
        account = acct("ravi@acme.example", login="2026-09-08T10:00:00Z")
        _, match, _ = run(account)
        self.assertEqual(last_login_evidence(account, match),
                         {"last_login_at": "2026-09-08T10:00:00Z", "available": True, "after_termination": False})

    def test_last_login_after_termination_is_flagged(self):
        account = acct("ravi@acme.example", login="2026-09-20T10:00:00Z")
        _, match, _ = run(account)
        self.assertTrue(last_login_evidence(account, match)["after_termination"])

    def test_last_login_unavailable_is_null_not_guessed(self):
        account = acct("ravi@acme.example", login=None)
        _, match, _ = run(account)
        self.assertEqual(last_login_evidence(account, match),
                         {"last_login_at": None, "available": False, "after_termination": None})

    def test_after_termination_not_asserted_for_low_confidence_match(self):
        account = acct("ravi.private@mail.example", "Ravi Kumar", login="2026-09-20T10:00:00Z")
        _, match, _ = run(account)
        self.assertIsNone(last_login_evidence(account, match)["after_termination"])


if __name__ == "__main__":
    unittest.main()
