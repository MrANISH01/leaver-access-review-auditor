"""Turn (account, match result, exclusion rules) into a classification, a reason and evidence.

Exclusions are checked FIRST and are explicit only: the source marks the account SHARED/SERVICE,
or it is listed in the exclusions table with a reason. We never guess from names like "admin@".
"""
from __future__ import annotations

from ..models import (AccountStatus, AccountType, Classification, Employee, EmploymentStatus,
                      EvidenceType, MatchConfidence, SaaSAccount)
from .matching import MatchResult


def exclusion_rules(account: SaaSAccount, exclusions: dict[tuple[str, str], dict]) -> list[dict]:
    rules: list[dict] = []
    if account.account_type in (AccountType.SHARED, AccountType.SERVICE):
        rules.append({
            "rule": "ACCOUNT_TYPE", "account_type": account.account_type.value,
            "summary": f"Source system marks this as a {account.account_type.value.lower()} account"})
    row = exclusions.get((account.system, account.external_account_id))
    if row is not None:
        rules.append({
            "rule": "EXPLICIT_EXCLUSION", "reason": row["reason"], "added_by": row["added_by"],
            "added_at": row["added_at"], "summary": f"Listed in exclusions: {row['reason']}"})
    return rules


def classify(account: SaaSAccount, match: MatchResult, rules: list[dict]) -> tuple[Classification, str]:
    if rules:
        return Classification.EXCLUDED, "Excluded from the individual leaver check. " + "; ".join(r["summary"] for r in rules)
    if match.needs_review:
        return Classification.NEEDS_REVIEW, match.note
    emp = match.employee
    if emp is None:
        return Classification.NO_MATCH, match.note
    if emp.employment_status is EmploymentStatus.TERMINATED:
        if account.status is AccountStatus.ACTIVE:
            return Classification.LEAVER_ACTIVE, f"Employee terminated {emp.termination_date} but account is still ACTIVE"
        return Classification.OK, f"Employee terminated {emp.termination_date}; account is already {account.status.value}"
    return Classification.OK, "Employee is active"


def is_deprovision_eligible(classification: str | Classification, confidence: str | MatchConfidence | None) -> bool:
    """Single rule for 'may a deprovisioning request be prepared?'. Stage 3 enforces this server-side."""
    return str(getattr(classification, "value", classification)) == Classification.LEAVER_ACTIVE.value \
        and str(getattr(confidence, "value", confidence)) == MatchConfidence.HIGH.value


def last_login_evidence(account: SaaSAccount, match: MatchResult) -> dict:
    """last_login_at is None when the source does not provide it; we never guess."""
    after = None
    emp = match.employee
    if (match.confidence is MatchConfidence.HIGH and emp is not None and emp.termination_date
            and account.last_login_at):
        after = account.last_login_at[:10] > emp.termination_date   # ISO dates compare lexicographically
    return {"last_login_at": account.last_login_at, "available": account.last_login_at is not None,
            "after_termination": after}


def hr_evidence(emp: Employee) -> dict:
    return emp.to_dict()


def build_evidence(account: SaaSAccount, match: MatchResult, rules: list[dict]) -> list[tuple[EvidenceType, dict]]:
    evidence: list[tuple[EvidenceType, dict]] = [(EvidenceType.ACCOUNT_RECORD, account.to_dict())]
    if rules:
        evidence.extend((EvidenceType.EXCLUSION_RULE, r) for r in rules)
        return evidence
    if match.employee is not None:
        evidence.append((EvidenceType.HR_RECORD, hr_evidence(match.employee)))
    evidence.append((EvidenceType.MATCH_RATIONALE, match.rationale))
    evidence.append((EvidenceType.LAST_LOGIN, last_login_evidence(account, match)))
    return evidence
