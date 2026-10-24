"""TC3: Exclude explicitly identified shared/service accounts from the individual leaver check."""
import unittest

from tests.base import AppTestCase, acct, emp


class TC3ExclusionTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.run_scan()
        self.by_account = self.findings_by_account()

    def test_service_and_shared_accounts_are_excluded(self):
        for account_id, atype in (("S-1005", "SERVICE"), ("G-2004", "SERVICE"), ("J-3003", "SHARED")):
            with self.subTest(account=account_id):
                f = self.by_account[account_id]
                self.assertEqual(f["classification"], "EXCLUDED")
                self.assertEqual(f["account"]["account_type"], atype)
                self.assertIsNone(f["employee"])
                self.assertIsNone(f["match_method"])
                self.assertFalse(f["deprovision_eligible"])
                (rule,) = self.evidence_of(f, "EXCLUSION_RULE")
                self.assertEqual((rule["rule"], rule["account_type"]), ("ACCOUNT_TYPE", atype))

    def test_explicit_exclusions_table_entry_is_honoured_with_its_reason(self):
        f = self.by_account["S-1006"]           # typed INDIVIDUAL by the source, but explicitly excluded
        self.assertEqual(f["account"]["account_type"], "INDIVIDUAL")
        self.assertEqual(f["classification"], "EXCLUDED")
        (rule,) = self.evidence_of(f, "EXCLUSION_RULE")
        self.assertEqual(rule["rule"], "EXPLICIT_EXCLUSION")
        self.assertIn("Shared on-call mailbox", rule["reason"])
        self.assertEqual(rule["added_by"], "it-ops@acme.example")

    def test_excluded_accounts_are_recorded_not_silently_dropped(self):
        excluded = self.findings(classification="EXCLUDED")
        self.assertEqual({f["account"]["external_account_id"] for f in excluded},
                         {"S-1005", "G-2004", "J-3003", "S-1006"})

    def test_no_excluded_account_is_ever_a_leaver_or_eligible(self):
        for f in self.findings(classification="EXCLUDED"):
            self.assertNotEqual(f["classification"], "LEAVER_ACTIVE")
            self.assertFalse(f["deprovision_eligible"])
        for f in self.findings(classification="LEAVER_ACTIVE"):
            self.assertNotEqual(f["account"]["account_type"], "SERVICE")
            self.assertNotEqual(f["account"]["account_type"], "SHARED")

    def test_exclusions_are_explicit_only_no_guessing_from_names(self):
        self.use_data(
            employees=[emp("E1", "Real Person", "real@acme.example", status="ACTIVE")],
            accounts=[acct("S-1", "admin@acme.example", "Admin"), acct("S-2", "svc-backup@acme.example", "svc backup")])
        self.run_scan()
        for f in self.findings():
            self.assertNotEqual(f["classification"], "EXCLUDED", f["account"]["external_account_id"])

    def test_service_account_with_a_leavers_email_is_still_excluded(self):
        self.use_data(
            employees=[emp("E1", "Ravi Kumar", "ravi@acme.example")],
            accounts=[acct("S-1", "ravi@acme.example", "Ravi Kumar", atype="SERVICE"),
                      acct("S-2", "ravi@acme.example", "Ravi Kumar", atype="SHARED"),
                      acct("S-3", "ravi@acme.example", "Ravi Kumar")])
        self.run_scan()
        f = self.findings_by_account()
        self.assertEqual(f["S-1"]["classification"], "EXCLUDED")
        self.assertEqual(f["S-2"]["classification"], "EXCLUDED")
        self.assertEqual(f["S-3"]["classification"], "LEAVER_ACTIVE")   # the individual one is still flagged

    def test_exclusions_row_beats_a_matching_leaver_email(self):
        self.use_data(
            employees=[emp("E1", "Ravi Kumar", "ravi@acme.example")],
            accounts=[acct("S-1", "ravi@acme.example", "Ravi Kumar")],
            exclusions=[{"system": "Slack", "external_account_id": "S-1", "reason": "Owner confirmed shared",
                         "added_by": "it@acme.example"}])
        self.run_scan()
        f = self.findings_by_account()["S-1"]
        self.assertEqual(f["classification"], "EXCLUDED")
        self.assertIsNone(f["employee"])

    def test_exclusions_seed_is_idempotent_across_restarts(self):
        from app import create_app
        before = self.raw_db().execute("SELECT COUNT(*) FROM exclusions").fetchone()[0]
        create_app(self.config)   # second startup on the same DB
        self.assertEqual(self.raw_db().execute("SELECT COUNT(*) FROM exclusions").fetchone()[0], before)
        self.assertEqual(before, 1)


if __name__ == "__main__":
    unittest.main()
