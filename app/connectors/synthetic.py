"""Synthetic HR source and SaaS connector backed by JSON files, plus fault injection.

State lives in memory inside the connector, entirely separate from our SQLite DB, so the
verifier's fresh read genuinely observes the "SaaS side". Run a single server process.
"""
from __future__ import annotations

import json
import threading
from dataclasses import replace
from pathlib import Path

from ..models import AccountStatus, ActionResult, Employee, FaultMode, SaaSAccount
from .base import AccountNotFound, ConnectorError, HRSource, SaaSConnector


def _read_json_list(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: expected a JSON list")
    return data


class SyntheticHRSource(HRSource):
    name = "synthetic"

    def __init__(self, path):
        path = Path(path)
        try:
            employees = [Employee.from_dict(r) for r in _read_json_list(path)]
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{path.name}: invalid employee record: {exc!r}") from exc
        self._employees = {}
        for e in employees:
            if e.employee_id in self._employees:
                raise ValueError(f"{path.name}: duplicate employee_id {e.employee_id}")
            self._employees[e.employee_id] = e

    def list_employees(self) -> list[Employee]:
        return list(self._employees.values())

    def get_employee(self, employee_id: str) -> Employee | None:
        return self._employees.get(employee_id)


class SyntheticConnector(SaaSConnector):
    name = "synthetic"

    def __init__(self, accounts_path):
        self._path = Path(accounts_path)
        self._lock = threading.RLock()
        self._accounts: dict[tuple[str, str], SaaSAccount] = {}
        self._default_fault = FaultMode.NONE
        self._account_faults: dict[tuple[str, str], FaultMode] = {}
        self.reset()

    # ---- demo controls (not part of the SaaSConnector interface) ----
    def reset(self) -> None:
        """Reload pristine account state from JSON and clear all injected faults."""
        try:
            accounts = [SaaSAccount.from_dict(r) for r in _read_json_list(self._path)]
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{self._path.name}: invalid account record: {exc!r}") from exc
        loaded: dict[tuple[str, str], SaaSAccount] = {}
        for a in accounts:
            key = (a.system, a.external_account_id)
            if key in loaded:
                raise ValueError(f"{self._path.name}: duplicate account {key}")
            loaded[key] = a
        with self._lock:
            self._accounts = loaded
            self.clear_faults()

    def set_fault(self, mode: FaultMode, system: str | None = None, external_account_id: str | None = None) -> None:
        if (system is None) != (external_account_id is None):
            raise ValueError("Provide both system and external_account_id, or neither")
        with self._lock:
            if system is None:
                self._default_fault = mode
            else:
                if (system, external_account_id) not in self._accounts:
                    raise AccountNotFound(f"{system}/{external_account_id}")
                self._account_faults[(system, external_account_id)] = mode

    def clear_faults(self) -> None:
        with self._lock:
            self._default_fault = FaultMode.NONE
            self._account_faults = {}

    def describe_faults(self) -> dict:
        with self._lock:
            return {
                "default": self._default_fault.value,
                "per_account": [
                    {"system": s, "external_account_id": i, "mode": m.value}
                    for (s, i), m in sorted(self._account_faults.items())
                ],
            }

    def _fault_for(self, key: tuple[str, str]) -> FaultMode:
        return self._account_faults.get(key, self._default_fault)

    # ---- SaaSConnector interface ----
    def list_systems(self) -> list[str]:
        with self._lock:
            return sorted({s for s, _ in self._accounts})

    def list_accounts(self, system: str | None = None) -> list[SaaSAccount]:
        with self._lock:
            return [a for a in self._accounts.values() if system is None or a.system == system]

    def get_account(self, system: str, external_account_id: str) -> SaaSAccount | None:
        with self._lock:
            return self._accounts.get((system, external_account_id))

    def disable_account(self, system: str, external_account_id: str) -> ActionResult:
        key = (system, external_account_id)
        with self._lock:
            account = self._accounts.get(key)
            if account is None:
                raise AccountNotFound(f"{system}/{external_account_id}")
            fault = self._fault_for(key)
            if fault is FaultMode.ERROR:
                raise ConnectorError(f"Injected fault: console error while disabling {system}/{external_account_id}")
            if fault is FaultMode.REJECT:
                return ActionResult(False, "Console rejected the request", {"status": "rejected"})
            if fault is FaultMode.SILENT_NOOP:
                # A lying console: claims success, changes nothing. Verification must catch this.
                return ActionResult(True, "Account disabled", {"status": "disabled"})
            self._accounts[key] = replace(account, status=AccountStatus.DISABLED)
            return ActionResult(True, "Account disabled", {"status": "disabled"})
