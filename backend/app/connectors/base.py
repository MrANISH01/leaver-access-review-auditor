"""Replaceable integration interfaces.

Member 3's mock-admin integration implements SaaSConnector in connectors/mock_admin.py.
There is deliberately NO delete method anywhere: the MVP can only disable accounts.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ActionResult, Employee, SaaSAccount


class ConnectorError(Exception):
    """The connector could not complete a call (network error, console error, injected fault...)."""


class AccountNotFound(ConnectorError):
    pass


class HRSource(ABC):
    """Source of truth for employment status. Failures should raise ConnectorError."""
    name: str

    @abstractmethod
    def list_employees(self) -> list[Employee]: ...

    @abstractmethod
    def get_employee(self, employee_id: str) -> Employee | None: ...


class SaaSConnector(ABC):
    name: str

    @abstractmethod
    def list_systems(self) -> list[str]:
        """Names of the SaaS systems this connector can reach (e.g. Slack, GitHub, Jira)."""

    @abstractmethod
    def list_accounts(self, system: str | None = None) -> list[SaaSAccount]:
        """All accounts, optionally for one system. Must reflect the live source, not a cache."""

    @abstractmethod
    def get_account(self, system: str, external_account_id: str) -> SaaSAccount | None:
        """Fresh read of one account; None if it does not exist. Used for independent verification."""

    @abstractmethod
    def disable_account(self, system: str, external_account_id: str) -> ActionResult:
        """Disable (never delete) an account. The result is a claim, to be verified separately.

        Raise AccountNotFound if the account does not exist, ConnectorError on other failures.
        """
