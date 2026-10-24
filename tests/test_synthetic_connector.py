import dataclasses
import json
import unittest
from collections import Counter
from pathlib import Path

from app.config import DEFAULT_DATA_DIR
from app.connectors.base import AccountNotFound, ConnectorError, HRSource, SaaSConnector
from app.connectors.synthetic import SyntheticConnector, SyntheticHRSource
from app.models import AccountStatus, AccountType, EmploymentStatus, FaultMode

DATA = Path(DEFAULT_DATA_DIR)


class SyntheticDataIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.accounts = SyntheticConnector(DATA / "accounts.json").list_accounts()
        self.hr = SyntheticHRSource(DATA / "employees.json")

    def test_three_systems(self):
        self.assertEqual(SyntheticConnector(DATA / "accounts.json").list_systems(), ["GitHub", "Jira", "Slack"])

    def test_covers_scenarios_needed_by_tc1_to_tc4(self):
        by_type = Counter(a.account_type for a in self.accounts)
        self.assertGreater(by_type[AccountType.SERVICE], 0)   # TC3
        self.assertGreater(by_type[AccountType.SHARED], 0)    # TC3
        self.assertTrue(any(a.last_login_at for a in self.accounts))          # TC1: login available
        self.assertTrue(any(a.last_login_at is None for a in self.accounts))  # TC1: login unavailable
        # TC2: an HR record whose name differs from the account display name but work email matches.
        priya = self.hr.get_employee("E102")
        acct = next(a for a in self.accounts if a.email == priya.work_email)
        self.assertNotEqual(priya.full_name, acct.display_name)
        self.assertEqual(priya.employment_status, EmploymentStatus.TERMINATED)

    def test_exclusions_reference_real_accounts(self):
        keys = {(a.system, a.external_account_id) for a in self.accounts}
        for row in json.loads((DATA / "exclusions.json").read_text()):
            self.assertIn((row["system"], row["external_account_id"]), keys)
            self.assertTrue(row["reason"])


class SyntheticHRSourceTests(unittest.TestCase):
    def test_lists_and_gets_employees(self):
        hr = SyntheticHRSource(DATA / "employees.json")
        self.assertIsInstance(hr, HRSource)
        self.assertEqual(len(hr.list_employees()), 6)
        self.assertEqual(hr.get_employee("E103").employment_status, EmploymentStatus.ACTIVE)
        self.assertIsNone(hr.get_employee("NOPE"))


class SyntheticConnectorTests(unittest.TestCase):
    def setUp(self):
        self.c = SyntheticConnector(DATA / "accounts.json")

    def test_implements_interface_and_has_no_delete(self):
        self.assertIsInstance(self.c, SaaSConnector)
        for attr in dir(self.c):
            self.assertNotIn("delete", attr.lower())

    def test_list_and_filter(self):
        self.assertEqual(len(self.c.list_accounts()), 16)
        self.assertTrue(all(a.system == "Slack" for a in self.c.list_accounts("Slack")))

    def test_last_login_none_when_unavailable(self):
        self.assertIsNone(self.c.get_account("Jira", "J-3001").last_login_at)
        self.assertEqual(self.c.get_account("Slack", "S-1001").last_login_at, "2026-09-14T17:42:00Z")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.c.get_account("Slack", "nope"))

    def test_disable_changes_state_and_is_observable(self):
        res = self.c.disable_account("Slack", "S-1001")
        self.assertTrue(res.success)
        self.assertEqual(self.c.get_account("Slack", "S-1001").status, AccountStatus.DISABLED)

    def test_disable_is_idempotent(self):
        self.c.disable_account("Slack", "S-1001")
        self.assertTrue(self.c.disable_account("Slack", "S-1001").success)

    def test_disable_unknown_account_raises(self):
        with self.assertRaises(AccountNotFound):
            self.c.disable_account("Slack", "nope")

    def test_returned_accounts_are_immutable(self):
        acct = self.c.get_account("Slack", "S-1001")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            acct.status = AccountStatus.DISABLED

    # ---- fault injection ----
    def test_silent_noop_claims_success_but_account_stays_active(self):
        self.c.set_fault(FaultMode.SILENT_NOOP)
        res = self.c.disable_account("Slack", "S-1001")
        self.assertTrue(res.success)  # the lie
        self.assertEqual(self.c.get_account("Slack", "S-1001").status, AccountStatus.ACTIVE)  # the truth

    def test_error_fault_raises_and_changes_nothing(self):
        self.c.set_fault(FaultMode.ERROR)
        with self.assertRaises(ConnectorError):
            self.c.disable_account("Slack", "S-1001")
        self.assertEqual(self.c.get_account("Slack", "S-1001").status, AccountStatus.ACTIVE)

    def test_reject_fault_reports_failure(self):
        self.c.set_fault(FaultMode.REJECT)
        self.assertFalse(self.c.disable_account("Slack", "S-1001").success)
        self.assertEqual(self.c.get_account("Slack", "S-1001").status, AccountStatus.ACTIVE)

    def test_per_account_fault_overrides_default_and_leaves_others_alone(self):
        self.c.set_fault(FaultMode.SILENT_NOOP, "Slack", "S-1001")
        self.c.disable_account("Slack", "S-1001")
        self.c.disable_account("Slack", "S-1002")
        self.assertEqual(self.c.get_account("Slack", "S-1001").status, AccountStatus.ACTIVE)
        self.assertEqual(self.c.get_account("Slack", "S-1002").status, AccountStatus.DISABLED)

    def test_per_account_none_overrides_global_fault(self):
        self.c.set_fault(FaultMode.ERROR)
        self.c.set_fault(FaultMode.NONE, "Slack", "S-1001")
        self.assertTrue(self.c.disable_account("Slack", "S-1001").success)

    def test_set_fault_requires_both_or_neither_target(self):
        with self.assertRaises(ValueError):
            self.c.set_fault(FaultMode.ERROR, system="Slack")

    def test_reset_restores_state_and_clears_faults(self):
        self.c.disable_account("Slack", "S-1001")
        self.c.set_fault(FaultMode.ERROR)
        self.c.reset()
        self.assertEqual(self.c.get_account("Slack", "S-1001").status, AccountStatus.ACTIVE)
        self.assertEqual(self.c.describe_faults(), {"default": "none", "per_account": []})


if __name__ == "__main__":
    unittest.main()
