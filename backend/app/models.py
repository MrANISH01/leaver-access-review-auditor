"""Domain types shared by connectors, services and the API (Stage 1 subset)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class AccountType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    SHARED = "SHARED"
    SERVICE = "SERVICE"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class EmploymentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    TERMINATED = "TERMINATED"


class Classification(str, Enum):
    LEAVER_ACTIVE = "LEAVER_ACTIVE"   # HIGH-confidence match to a terminated employee, account still ACTIVE
    EXCLUDED = "EXCLUDED"             # explicit shared/service exclusion: never an individual leaver
    NEEDS_REVIEW = "NEEDS_REVIEW"     # identity not verified (name-only, ambiguous or conflicting)
    NO_MATCH = "NO_MATCH"             # no HR record matched
    OK = "OK"                         # active employee, or leaver whose account is already disabled


class MatchMethod(str, Enum):
    WORK_EMAIL = "WORK_EMAIL"
    EMPLOYEE_ID = "EMPLOYEE_ID"
    NAME_ONLY = "NAME_ONLY"


class MatchConfidence(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class EvidenceType(str, Enum):
    HR_RECORD = "HR_RECORD"
    ACCOUNT_RECORD = "ACCOUNT_RECORD"
    MATCH_RATIONALE = "MATCH_RATIONALE"
    EXCLUSION_RULE = "EXCLUSION_RULE"
    LAST_LOGIN = "LAST_LOGIN"


class RequestStatus(str, Enum):
    PREPARED = "PREPARED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    EXECUTED_UNVERIFIED = "EXECUTED_UNVERIFIED"
    VERIFIED = "VERIFIED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


# The ONLY legal transitions. Note that EXECUTING is reachable from APPROVED and nothing else.
ALLOWED_TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.PREPARED: frozenset({RequestStatus.APPROVED, RequestStatus.REJECTED}),
    RequestStatus.APPROVED: frozenset({RequestStatus.EXECUTING}),
    RequestStatus.EXECUTING: frozenset({RequestStatus.EXECUTED_UNVERIFIED, RequestStatus.EXECUTION_FAILED}),
    RequestStatus.EXECUTED_UNVERIFIED: frozenset({RequestStatus.VERIFIED, RequestStatus.VERIFICATION_FAILED}),
    RequestStatus.REJECTED: frozenset(),
    RequestStatus.EXECUTION_FAILED: frozenset(),
    RequestStatus.VERIFIED: frozenset(),
    RequestStatus.VERIFICATION_FAILED: frozenset(),
}


def can_transition(current: str, target: str) -> bool:
    try:
        return RequestStatus(target) in ALLOWED_TRANSITIONS[RequestStatus(current)]
    except (ValueError, KeyError):
        return False


class FaultMode(str, Enum):
    """Synthetic-connector fault injection (used to test verification honestly)."""
    NONE = "none"
    SILENT_NOOP = "silent_noop"   # disable_account reports success but changes nothing (a lying console)
    ERROR = "error"               # disable_account raises ConnectorError
    REJECT = "reject"             # disable_account returns success=False


def _plain(data: dict) -> dict:
    return {k: (v.value if isinstance(v, Enum) else v) for k, v in data.items()}


@dataclass(frozen=True)
class Employee:
    employee_id: str
    full_name: str
    work_email: str
    employment_status: EmploymentStatus
    termination_date: str | None = None
    department: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Employee":
        return cls(
            employee_id=d["employee_id"],
            full_name=d["full_name"],
            work_email=d["work_email"],
            employment_status=EmploymentStatus(d["employment_status"]),
            termination_date=d.get("termination_date"),
            department=d.get("department"),
        )

    def to_dict(self) -> dict:
        return _plain(asdict(self))


@dataclass(frozen=True)
class SaaSAccount:
    system: str
    external_account_id: str
    email: str | None
    display_name: str | None
    username: str | None
    account_type: AccountType
    status: AccountStatus
    last_login_at: str | None = None   # None = unavailable from the source; never guessed
    employee_id: str | None = None     # only when the source system carries it

    @classmethod
    def from_dict(cls, d: dict) -> "SaaSAccount":
        return cls(
            system=d["system"],
            external_account_id=d["external_account_id"],
            email=d.get("email"),
            display_name=d.get("display_name"),
            username=d.get("username"),
            account_type=AccountType(d["account_type"]),
            status=AccountStatus(d["status"]),
            last_login_at=d.get("last_login_at"),
            employee_id=d.get("employee_id"),
        )

    def to_dict(self) -> dict:
        return _plain(asdict(self))


@dataclass(frozen=True)
class ActionResult:
    """What a connector CLAIMS happened. Never proof: only an independent read is proof."""
    success: bool
    message: str
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
