"""Deterministic HR-to-SaaS identity matching. Pure functions: no DB, no I/O, no ML.

Order of evidence (most to least trustworthy):
  1. Verified work email (case-insensitive exact match to the HR work_email)  -> HIGH
  2. employee_id carried on the account                                        -> HIGH
  3. Display name only                                                         -> LOW, always NEEDS_REVIEW

Conservative rules: anything ambiguous or contradictory is NEEDS_REVIEW and is never linked with
HIGH confidence. A name match can never make an account eligible for deprovisioning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ..models import Employee, MatchConfidence, MatchMethod, SaaSAccount


def normalize_email(value: str | None) -> str | None:
    value = (value or "").strip().lower()
    return value or None


def normalize_name(value: str | None) -> str | None:
    value = " ".join((value or "").casefold().split())
    return value or None


class EmployeeIndex:
    def __init__(self, employees: Iterable[Employee]):
        self.by_id: dict[str, Employee] = {}
        self.by_email: dict[str, list[Employee]] = {}
        self.by_name: dict[str, list[Employee]] = {}
        for e in employees:
            self.by_id[e.employee_id] = e
            if (email := normalize_email(e.work_email)):
                self.by_email.setdefault(email, []).append(e)
            if (name := normalize_name(e.full_name)):
                self.by_name.setdefault(name, []).append(e)


@dataclass(frozen=True)
class MatchResult:
    employee: Employee | None
    method: MatchMethod | None
    confidence: MatchConfidence | None
    needs_review: bool
    note: str
    rationale: dict = field(default_factory=dict)   # JSON-safe; stored as MATCH_RATIONALE evidence


def _surname_note(account_name: str | None, hr_name: str) -> tuple[bool | None, str]:
    """Return (names_differ, note). names_differ is None when the account has no display name."""
    a, h = normalize_name(account_name), normalize_name(hr_name)
    if a is None:
        return None, ""
    if a == h:
        return False, ""
    a_parts, h_parts = a.split(), h.split()
    if len(a_parts) > 1 and len(h_parts) > 1 and a_parts[0] == h_parts[0]:
        return True, (f"Last name differs ('{account_name.split()[-1]}' on the account vs "
                      f"'{hr_name.split()[-1]}' in HR)")
    return True, f"Display name '{account_name}' differs from HR name '{hr_name}'"


def _confident(account: SaaSAccount, emp: Employee, method: MatchMethod, id_corroborates: bool) -> MatchResult:
    differs, diff_note = _surname_note(account.display_name, emp.full_name)
    if method is MatchMethod.WORK_EMAIL:
        note = f"Matched on verified work email {emp.work_email}"
        if id_corroborates:
            note += "; employee_id on the account agrees"
    else:
        note = f"Matched on employee_id {emp.employee_id} carried by the account"
    if differs:
        note += f". {diff_note}; identity rests on the {'work email' if method is MatchMethod.WORK_EMAIL else 'employee_id'}, not the name"
    return MatchResult(
        employee=emp, method=method, confidence=MatchConfidence.HIGH, needs_review=False, note=note,
        rationale={"method": method.value, "confidence": "HIGH", "note": note,
                   "account_email": account.email, "hr_work_email": emp.work_email,
                   "account_display_name": account.display_name, "hr_full_name": emp.full_name,
                   "name_differs": differs, "employee_id_corroborates": id_corroborates})


def _review(employee: Employee | None, method: MatchMethod | None, note: str, **extra) -> MatchResult:
    confidence = MatchConfidence.LOW if method is MatchMethod.NAME_ONLY else None
    return MatchResult(
        employee=employee, method=method, confidence=confidence, needs_review=True, note=note,
        rationale={"method": method.value if method else None,
                   "confidence": confidence.value if confidence else None, "note": note, **extra})


def match_account(account: SaaSAccount, index: EmployeeIndex) -> MatchResult:
    email = normalize_email(account.email)
    email_hits = index.by_email.get(email, []) if email else []
    id_hit = index.by_id.get(account.employee_id) if account.employee_id else None

    if len(email_hits) > 1:
        return _review(None, None, "Account email matches more than one HR record; identity is ambiguous",
                       candidates=[e.employee_id for e in email_hits])

    if len(email_hits) == 1:
        emp = email_hits[0]
        if id_hit is not None and id_hit.employee_id != emp.employee_id:
            return _review(None, None,
                           f"Conflicting identity: work email points to {emp.employee_id} but the account's "
                           f"employee_id points to {id_hit.employee_id}",
                           candidates=[emp.employee_id, id_hit.employee_id])
        return _confident(account, emp, MatchMethod.WORK_EMAIL, id_corroborates=id_hit is not None)

    if id_hit is not None:
        return _confident(account, id_hit, MatchMethod.EMPLOYEE_ID, id_corroborates=False)

    name = normalize_name(account.display_name)
    name_hits = index.by_name.get(name, []) if name else []
    if len(name_hits) == 1:
        emp = name_hits[0]
        return _review(emp, MatchMethod.NAME_ONLY,
                       f"Name-only match to {emp.employee_id} ('{emp.full_name}'): the account email does not match "
                       "any HR work email and no employee_id is present. Identity is unverified; a reviewer must confirm",
                       account_email=account.email, hr_work_email=emp.work_email,
                       account_display_name=account.display_name, hr_full_name=emp.full_name)
    if len(name_hits) > 1:
        return _review(None, MatchMethod.NAME_ONLY,
                       "Display name matches more than one HR record; identity is ambiguous",
                       candidates=[e.employee_id for e in name_hits])

    return MatchResult(
        employee=None, method=None, confidence=None, needs_review=False,
        note="No HR record matched by work email, employee_id or name",
        rationale={"method": None, "confidence": None,
                   "note": "No HR record matched by work email, employee_id or name",
                   "account_email": account.email, "account_display_name": account.display_name})
