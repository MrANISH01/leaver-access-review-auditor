# Leaver Access Review Auditor: API contract (Stages 1-4)

Base URL (local): `http://127.0.0.1:5001/api/v1`. JSON only. All samples below were captured from the running
backend on the synthetic data, not written by hand.

**Status:** Stages 1-4 endpoints are stable (including scan, prepare / approve / reject, execute, independent verification, and the audit log).
Changes from here are **additive only** (new endpoints or new fields);
existing paths and field names will not be renamed or removed without telling you both.

## Conventions

- Success: `{"data": ...}` (lists also carry `"meta"`). Error: `{"error": {"code": "...", "message": "..."}}`.
- Status codes: 200 / 201 OK, 400 bad request, 404 not found, 405 wrong method, 409 conflict/state error, 422 validation, 502 source system unavailable.
- `X-Actor` header (e.g. `alice@acme.example`) is required on every **POST/DELETE** and on `GET /whoami`. It is a **demo-only label for
  the audit trail, not authentication**. Never rely on the frontend to enforce approval: the server decides.
- CORS: only the origin set in the server's `FRONTEND_ORIGIN` is allowed. Tell Member 1 your dev origin
  (for example `http://localhost:5173`); there is no wildcard. If you proxy through your dev server you need no CORS at all.
- `last_login_at` is `null` when the source system does not provide it. Show **"unavailable"**, never a guess.
- Timestamps are ISO-8601 UTC strings.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | liveness, connector name, `demo_mode` |
| POST | `/scans` | needs `X-Actor`. Runs a **read-only** scan now (201). 502 `SOURCE_UNAVAILABLE` if a source fails |
| GET | `/scans` | newest first |
| GET | `/scans/{id}` | 404 if unknown |
| GET | `/findings?scan_id=&classification=&system=` | defaults to the **latest completed** scan. Items have no `evidence` |
| GET | `/findings/{id}` | adds `evidence[]` |
| GET | `/summary` | dashboard counts (`pending_approval` = requests in PREPARED, `verified` = requests in VERIFIED) |
| POST | `/findings/{id}/deprovision-requests` | needs `X-Actor`. **Prepares** a disable request (201). Does not touch the account |
| GET | `/deprovision-requests?status=` | newest first, each with a nested `finding` |
| GET | `/deprovision-requests/{id}` | adds `executions[]` and `verifications[]` |
| POST | `/deprovision-requests/{id}/approve` | needs `X-Actor` on the approver allowlist. Optional body `{"note": "..."}` |
| POST | `/deprovision-requests/{id}/reject` | same rules. A preparer may reject their own request (withdrawal) |
| POST | `/deprovision-requests/{id}/execute` | needs `X-Actor`. Executes an approved request with live prechecks and independent verification |
| GET | `/audit-log?entity_type=&entity_id=&event=&limit=` | append-only trail, oldest first, `limit` 1-500 (default 200) |
| GET | `/whoami` | needs `X-Actor`. `{actor, can_approve}`: a UI hint for showing Approve/Reject buttons |
| POST | `/dev/reset` | demo mode only. Wipes DB + reseeds + resets the synthetic SaaS state |
| GET | `/dev/connector/accounts` | demo mode only. Live connector state (ground truth, not our DB) |
| GET / POST / DELETE | `/dev/fault-injection` | demo mode only. Used to test failed verification |

`classification` values: `LEAVER_ACTIVE`, `EXCLUDED`, `NEEDS_REVIEW`, `NO_MATCH`, `OK`.
`match_method`: `WORK_EMAIL`, `EMPLOYEE_ID`, `NAME_ONLY` (or `null`). `match_confidence`: `HIGH`, `LOW` (or `null`).
Evidence `type`: `ACCOUNT_RECORD`, `HR_RECORD`, `MATCH_RATIONALE`, `LAST_LOGIN`, `EXCLUSION_RULE`.

## What each classification means (for UI labels)

| Classification | Meaning | Can a deprovision request be prepared? |
|---|---|---|
| `LEAVER_ACTIVE` | HIGH-confidence match to a terminated employee and the account is still ACTIVE | Yes (`deprovision_eligible: true`) |
| `NEEDS_REVIEW` | Identity not verified: name-only, ambiguous or conflicting signals | **No** |
| `EXCLUDED` | Explicit shared/service account. Never an individual leaver | **No** |
| `NO_MATCH` | No HR record matched | **No** |
| `OK` | Active employee, or a leaver whose account is already disabled | **No** |

`deprovision_eligible` is a UI hint. The server re-checks it when a request is prepared, so hiding or showing a button
is cosmetic, not security.

## Samples

### POST /scans  (201)
```json
{
  "data": {
    "connector": "synthetic",
    "finished_at": "2026-10-21T09:02:32Z",
    "id": 1,
    "started_at": "2026-10-21T09:02:32Z",
    "status": "COMPLETED",
    "summary": {
      "by_classification": {
        "EXCLUDED": 4,
        "LEAVER_ACTIVE": 7,
        "NEEDS_REVIEW": 1,
        "NO_MATCH": 0,
        "OK": 4
      },
      "employees_synced": 6,
      "systems": [
        "GitHub",
        "Jira",
        "Slack"
      ],
      "total_accounts": 16
    }
  }
}
```

### GET /findings: one list item (TC2: surname changed, matched on work email)
```json
{
  "account": {
    "account_type": "INDIVIDUAL",
    "display_name": "Priya Sharma",
    "email": "priya.sharma@acme.example",
    "employee_id": null,
    "external_account_id": "S-1002",
    "id": 2,
    "last_login_at": "2026-09-28T09:14:00Z",
    "status": "ACTIVE",
    "system": "Slack",
    "username": "priya.sharma"
  },
  "classification": "LEAVER_ACTIVE",
  "created_at": "2026-10-21T09:02:32Z",
  "deprovision_eligible": true,
  "employee": {
    "department": "Finance",
    "employee_id": "E102",
    "employment_status": "TERMINATED",
    "full_name": "Priya Nair",
    "termination_date": "2026-09-30",
    "work_email": "priya.sharma@acme.example"
  },
  "id": 2,
  "match_confidence": "HIGH",
  "match_method": "WORK_EMAIL",
  "reason": "Employee terminated 2026-09-30 but account is still ACTIVE",
  "scan_id": 1
}
```

### GET /findings/{id}: same finding with evidence
```json
{
  "data": {
    "account": {
      "account_type": "INDIVIDUAL",
      "display_name": "Priya Sharma",
      "email": "priya.sharma@acme.example",
      "employee_id": null,
      "external_account_id": "S-1002",
      "id": 2,
      "last_login_at": "2026-09-28T09:14:00Z",
      "status": "ACTIVE",
      "system": "Slack",
      "username": "priya.sharma"
    },
    "classification": "LEAVER_ACTIVE",
    "created_at": "2026-10-21T09:02:32Z",
    "deprovision_eligible": true,
    "employee": {
      "department": "Finance",
      "employee_id": "E102",
      "employment_status": "TERMINATED",
      "full_name": "Priya Nair",
      "termination_date": "2026-09-30",
      "work_email": "priya.sharma@acme.example"
    },
    "evidence": [
      {
        "created_at": "2026-10-21T09:02:32Z",
        "detail": {
          "account_type": "INDIVIDUAL",
          "display_name": "Priya Sharma",
          "email": "priya.sharma@acme.example",
          "employee_id": null,
          "external_account_id": "S-1002",
          "last_login_at": "2026-09-28T09:14:00Z",
          "status": "ACTIVE",
          "system": "Slack",
          "username": "priya.sharma"
        },
        "id": 5,
        "type": "ACCOUNT_RECORD"
      },
      {
        "created_at": "2026-10-21T09:02:32Z",
        "detail": {
          "department": "Finance",
          "employee_id": "E102",
          "employment_status": "TERMINATED",
          "full_name": "Priya Nair",
          "termination_date": "2026-09-30",
          "work_email": "priya.sharma@acme.example"
        },
        "id": 6,
        "type": "HR_RECORD"
      },
      {
        "created_at": "2026-10-21T09:02:32Z",
        "detail": {
          "account_display_name": "Priya Sharma",
          "account_email": "priya.sharma@acme.example",
          "confidence": "HIGH",
          "employee_id_corroborates": false,
          "hr_full_name": "Priya Nair",
          "hr_work_email": "priya.sharma@acme.example",
          "method": "WORK_EMAIL",
          "name_differs": true,
          "note": "Matched on verified work email priya.sharma@acme.example. Last name differs ('Sharma' on the account vs 'Nair' in HR); identity rests on the work email, not the name"
        },
        "id": 7,
        "type": "MATCH_RATIONALE"
      },
      {
        "created_at": "2026-10-21T09:02:32Z",
        "detail": {
          "after_termination": false,
          "available": true,
          "last_login_at": "2026-09-28T09:14:00Z"
        },
        "id": 8,
        "type": "LAST_LOGIN"
      }
    ],
    "id": 2,
    "match_confidence": "HIGH",
    "match_method": "WORK_EMAIL",
    "reason": "Employee terminated 2026-09-30 but account is still ACTIVE",
    "scan_id": 1
  }
}
```

### GET /findings/{id}: TC1 with last login unavailable
Only the relevant part: `account.last_login_at` is `null` and the LAST_LOGIN evidence says so.
```json
{
  "account_last_login_at": null,
  "last_login_evidence": {
    "after_termination": null,
    "available": false,
    "last_login_at": null
  }
}
```

### GET /findings/{id}: TC3 excluded service account
```json
{
  "data": {
    "account": {
      "account_type": "SERVICE",
      "display_name": "IT Alerts Bot",
      "email": "it-alerts@acme.example",
      "employee_id": null,
      "external_account_id": "S-1005",
      "id": 5,
      "last_login_at": null,
      "status": "ACTIVE",
      "system": "Slack",
      "username": "it-alerts"
    },
    "classification": "EXCLUDED",
    "created_at": "2026-10-21T09:02:32Z",
    "deprovision_eligible": false,
    "employee": null,
    "evidence": [
      {
        "created_at": "2026-10-21T09:02:32Z",
        "detail": {
          "account_type": "SERVICE",
          "display_name": "IT Alerts Bot",
          "email": "it-alerts@acme.example",
          "employee_id": null,
          "external_account_id": "S-1005",
          "last_login_at": null,
          "status": "ACTIVE",
          "system": "Slack",
          "username": "it-alerts"
        },
        "id": 17,
        "type": "ACCOUNT_RECORD"
      },
      {
        "created_at": "2026-10-21T09:02:32Z",
        "detail": {
          "account_type": "SERVICE",
          "rule": "ACCOUNT_TYPE",
          "summary": "Source system marks this as a service account"
        },
        "id": 18,
        "type": "EXCLUSION_RULE"
      }
    ],
    "id": 5,
    "match_confidence": null,
    "match_method": null,
    "reason": "Excluded from the individual leaver check. Source system marks this as a service account",
    "scan_id": 1
  }
}
```

### Name-only match (list item): NEEDS_REVIEW, not eligible
```json
{
  "account": {
    "account_type": "INDIVIDUAL",
    "display_name": "Karan Singh",
    "email": "karan.singh.personal@mailbox.example",
    "employee_id": null,
    "external_account_id": "G-2005",
    "id": 11,
    "last_login_at": "2026-10-04T08:30:00Z",
    "status": "ACTIVE",
    "system": "GitHub",
    "username": "karan-singh-codes"
  },
  "classification": "NEEDS_REVIEW",
  "created_at": "2026-10-21T09:02:32Z",
  "deprovision_eligible": false,
  "employee": {
    "department": "Engineering",
    "employee_id": "E105",
    "employment_status": "TERMINATED",
    "full_name": "Karan Singh",
    "termination_date": "2026-10-05",
    "work_email": "karan.singh@acme.example"
  },
  "id": 11,
  "match_confidence": "LOW",
  "match_method": "NAME_ONLY",
  "reason": "Name-only match to E105 ('Karan Singh'): the account email does not match any HR work email and no employee_id is present. Identity is unverified; a reviewer must confirm",
  "scan_id": 1
}
```

### GET /summary
```json
{
  "data": {
    "excluded": 4,
    "findings_by_classification": {
      "EXCLUDED": 4,
      "LEAVER_ACTIVE": 7,
      "NEEDS_REVIEW": 1,
      "NO_MATCH": 0,
      "OK": 4
    },
    "latest_scan": {
      "finished_at": "2026-10-21T09:02:32Z",
      "id": 1
    },
    "leavers_active": 7,
    "needs_review": 1,
    "pending_approval": 0,
    "total_findings": 16,
    "verified": 0
  }
}
```
`pending_approval` and `verified` stay `0` until Stages 3-4.

### Error example (GET /findings?classification=BOGUS, 422)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "classification must be one of ['LEAVER_ACTIVE', 'EXCLUDED', 'NEEDS_REVIEW', 'NO_MATCH', 'OK']"
  }
}
```


---

# Stage 3: deprovisioning requests, approval and audit

**Rules the server enforces (the frontend cannot override any of them):**

1. Only a finding with `deprovision_eligible: true` (HIGH-confidence `LEAVER_ACTIVE`, individual account, not
   excluded, from the **latest** scan) can have a request prepared. Anything else is `422 NOT_ELIGIBLE`.
2. **Preparing, approving and rejecting never disable anything.** Disabling arrives in Stage 4 and will only run for `APPROVED` requests.
3. Approve/reject requires the `X-Actor` to be on the server's `APPROVER_ACTORS` allowlist. If the allowlist is empty, nobody can approve.
4. **Separation of duties:** the approver cannot be the person who prepared the request (case-insensitive).
5. One open request per account. A rejected request frees the account for a new one.
6. Decisions are atomic. Repeating the *same* decision by the *same* actor is an idempotent replay (200, `meta.idempotent_replay: true`).
7. Every attempt, successful or refused, is written to the audit log.

**Request statuses:** `PREPARED` -> `APPROVED` or `REJECTED`. Later (Stage 4): `EXECUTING`, `EXECUTED_UNVERIFIED`,
`VERIFIED`, `EXECUTION_FAILED`, `VERIFICATION_FAILED`. `verified` is `true` **only** when status is `VERIFIED`.
`APPROVED` means "a human authorised this", not "the account is disabled".

**Suggested UI wiring**
- Show **Prepare request** when `finding.deprovision_eligible` is true and no open request exists for that account
  (`GET /deprovision-requests` and match on `system` + `external_account_id`; `DUPLICATE_REQUEST` is the server-side backstop).
- Call `GET /whoami` once and show **Approve / Reject** only when `can_approve` is true. It is cosmetic: the server decides.
- Treat 403 `SELF_APPROVAL_FORBIDDEN` as "ask a different approver".
- Label `APPROVED` as "Approved, awaiting execution", never "Disabled" or "Done".

## Error codes added in Stage 3

| HTTP | `code` | When |
|---|---|---|
| 422 | `NOT_ELIGIBLE` | finding is not an eligible leaver (`details` has the classification) |
| 409 | `STALE_FINDING` | finding is from an older scan; rescan and use the new finding |
| 409 | `DUPLICATE_REQUEST` | an open request already exists for the account (`details.existing_request_id`) |
| 403 | `APPROVER_NOT_AUTHORIZED` | actor is not on the allowlist (or none configured) |
| 403 | `SELF_APPROVAL_FORBIDDEN` | approver prepared this request |
| 409 | `INVALID_STATE` | e.g. approving a REJECTED request, rejecting an APPROVED one (`details.current_status`) |
| 422 | `VALIDATION_ERROR` | `note` not a string or over 500 characters |

Errors may now carry an optional `details` object next to `code` and `message`.

## Stage 3 samples (captured from the running backend)

### POST /findings/{id}/deprovision-requests (201)
```json
{
  "data": {
    "action": "DISABLE",
    "decided_at": null,
    "decided_by": null,
    "decision_note": null,
    "executed_at": null,
    "executions": [],
    "expected_status": "DISABLED",
    "external_account_id": "S-1002",
    "finding": {
      "account": {
        "account_type": "INDIVIDUAL",
        "display_name": "Priya Sharma",
        "email": "priya.sharma@acme.example",
        "employee_id": null,
        "external_account_id": "S-1002",
        "id": 2,
        "last_login_at": "2026-09-28T09:14:00Z",
        "status": "ACTIVE",
        "system": "Slack",
        "username": "priya.sharma"
      },
      "classification": "LEAVER_ACTIVE",
      "employee": {
        "department": "Finance",
        "employee_id": "E102",
        "employment_status": "TERMINATED",
        "full_name": "Priya Nair",
        "termination_date": "2026-09-30",
        "work_email": "priya.sharma@acme.example"
      },
      "id": 2,
      "match_confidence": "HIGH",
      "match_method": "WORK_EMAIL",
      "reason": "Employee terminated 2026-09-30 but account is still ACTIVE",
      "scan_id": 1
    },
    "finding_id": 2,
    "id": 1,
    "idempotency_key": "deprov-2-060f4be5ad2a4335a78f42ae51df78ca",
    "prepared_at": "2026-10-22T05:11:00Z",
    "prepared_by": "preparer@acme.example",
    "status": "PREPARED",
    "system": "Slack",
    "verifications": [],
    "verified": false,
    "verified_at": null
  }
}
```

### POST /deprovision-requests/{id}/approve (200)
```json
{
  "data": {
    "action": "DISABLE",
    "decided_at": "2026-10-22T05:11:00Z",
    "decided_by": "approver@acme.example",
    "decision_note": "Confirmed with HR",
    "executed_at": null,
    "executions": [],
    "expected_status": "DISABLED",
    "external_account_id": "S-1002",
    "finding": {
      "account": {
        "account_type": "INDIVIDUAL",
        "display_name": "Priya Sharma",
        "email": "priya.sharma@acme.example",
        "employee_id": null,
        "external_account_id": "S-1002",
        "id": 2,
        "last_login_at": "2026-09-28T09:14:00Z",
        "status": "ACTIVE",
        "system": "Slack",
        "username": "priya.sharma"
      },
      "classification": "LEAVER_ACTIVE",
      "employee": {
        "department": "Finance",
        "employee_id": "E102",
        "employment_status": "TERMINATED",
        "full_name": "Priya Nair",
        "termination_date": "2026-09-30",
        "work_email": "priya.sharma@acme.example"
      },
      "id": 2,
      "match_confidence": "HIGH",
      "match_method": "WORK_EMAIL",
      "reason": "Employee terminated 2026-09-30 but account is still ACTIVE",
      "scan_id": 1
    },
    "finding_id": 2,
    "id": 1,
    "idempotency_key": "deprov-2-060f4be5ad2a4335a78f42ae51df78ca",
    "prepared_at": "2026-10-22T05:11:00Z",
    "prepared_by": "preparer@acme.example",
    "status": "APPROVED",
    "system": "Slack",
    "verifications": [],
    "verified": false,
    "verified_at": null
  },
  "meta": {
    "idempotent_replay": false
  }
}
```

### Repeating the same approval (200, idempotent replay): only `meta` differs
```json
{
  "data": {
    "id": 1,
    "finding_id": 2,
    "system": "Slack",
    "external_account_id": "S-1002",
    "status": "APPROVED",
    "verified": false,
    "prepared_by": "preparer@acme.example",
    "decided_by": "approver@acme.example"
  },
  "meta": {
    "idempotent_replay": true
  }
}
```

### POST /deprovision-requests/{id}/reject (200)
```json
{
  "data": {
    "id": 3,
    "finding_id": 13,
    "system": "Jira",
    "external_account_id": "J-3002",
    "status": "REJECTED",
    "verified": false,
    "prepared_by": "preparer@acme.example",
    "decided_by": "approver@acme.example",
    "decision_note": "Still on notice period"
  },
  "meta": {
    "idempotent_replay": false
  }
}
```

### GET /deprovision-requests?status=APPROVED (list item shape)
```json
{
  "action": "DISABLE",
  "decided_at": "2026-10-22T05:11:00Z",
  "decided_by": "approver@acme.example",
  "decision_note": "Confirmed with HR",
  "executed_at": null,
  "expected_status": "DISABLED",
  "external_account_id": "S-1002",
  "finding": {
    "account": {
      "account_type": "INDIVIDUAL",
      "display_name": "Priya Sharma",
      "email": "priya.sharma@acme.example",
      "employee_id": null,
      "external_account_id": "S-1002",
      "id": 2,
      "last_login_at": "2026-09-28T09:14:00Z",
      "status": "ACTIVE",
      "system": "Slack",
      "username": "priya.sharma"
    },
    "classification": "LEAVER_ACTIVE",
    "employee": {
      "department": "Finance",
      "employee_id": "E102",
      "employment_status": "TERMINATED",
      "full_name": "Priya Nair",
      "termination_date": "2026-09-30",
      "work_email": "priya.sharma@acme.example"
    },
    "id": 2,
    "match_confidence": "HIGH",
    "match_method": "WORK_EMAIL",
    "reason": "Employee terminated 2026-09-30 but account is still ACTIVE",
    "scan_id": 1
  },
  "finding_id": 2,
  "id": 1,
  "idempotency_key": "deprov-2-060f4be5ad2a4335a78f42ae51df78ca",
  "prepared_at": "2026-10-22T05:11:00Z",
  "prepared_by": "preparer@acme.example",
  "status": "APPROVED",
  "system": "Slack",
  "verified": false,
  "verified_at": null
}
```

### Refusals
Not eligible (name-only match), 422:
```json
{
  "error": {
    "code": "NOT_ELIGIBLE",
    "details": {
      "classification": "NEEDS_REVIEW",
      "match_confidence": "LOW"
    },
    "message": "Finding is NEEDS_REVIEW (match confidence LOW); only HIGH-confidence LEAVER_ACTIVE findings can have a deprovisioning request prepared"
  }
}
```
Duplicate, 409:
```json
{
  "error": {
    "code": "DUPLICATE_REQUEST",
    "details": {
      "existing_request_id": 1,
      "existing_status": "PREPARED"
    },
    "message": "An open request (PREPARED) already exists for this account: #1"
  }
}
```
Actor not on the allowlist, 403:
```json
{
  "error": {
    "code": "APPROVER_NOT_AUTHORIZED",
    "message": "This actor is not on the approver allowlist"
  }
}
```
Self-approval by an allowlisted approver, 403:
```json
{
  "error": {
    "code": "SELF_APPROVAL_FORBIDDEN",
    "details": {
      "prepared_by": "approver@acme.example"
    },
    "message": "The person who prepared a request cannot approve it"
  }
}
```
Invalid state transition, 409:
```json
{
  "error": {
    "code": "INVALID_STATE",
    "details": {
      "attempted": "REJECTED",
      "current_status": "APPROVED"
    },
    "message": "Cannot reject a request that is APPROVED"
  }
}
```

### GET /whoami
```json
{
  "data": {
    "actor": "approver@acme.example",
    "can_approve": true
  }
}
```

### GET /audit-log?entity_type=deprovision_request&entity_id=1
```json
{
  "data": [
    {
      "actor": "preparer@acme.example",
      "detail": {
        "action": "DISABLE",
        "employee_id": "E102",
        "external_account_id": "S-1002",
        "finding_id": 2,
        "system": "Slack"
      },
      "entity_id": "1",
      "entity_type": "deprovision_request",
      "event": "DEPROVISION_PREPARED",
      "id": 3,
      "ts": "2026-10-22T05:11:00Z"
    },
    {
      "actor": "mallory@acme.example",
      "detail": {
        "code": "APPROVER_NOT_AUTHORIZED",
        "reason": "UNAUTHORIZED_APPROVER"
      },
      "entity_id": "1",
      "entity_type": "deprovision_request",
      "event": "DEPROVISION_APPROVE_DENIED",
      "id": 6,
      "ts": "2026-10-22T05:11:00Z"
    },
    {
      "actor": "approver@acme.example",
      "detail": {
        "external_account_id": "S-1002",
        "from": "PREPARED",
        "note": "Confirmed with HR",
        "prepared_by": "preparer@acme.example",
        "system": "Slack",
        "to": "APPROVED"
      },
      "entity_id": "1",
      "entity_type": "deprovision_request",
      "event": "DEPROVISION_APPROVED",
      "id": 9,
      "ts": "2026-10-22T05:11:00Z"
    },
    {
      "actor": "approver@acme.example",
      "detail": {
        "decision": "APPROVED",
        "status": "APPROVED"
      },
      "entity_id": "1",
      "entity_type": "deprovision_request",
      "event": "DEPROVISION_DECISION_REPLAYED",
      "id": 10,
      "ts": "2026-10-22T05:11:00Z"
    },
    {
      "actor": "approver@acme.example",
      "detail": {
        "attempted": "REJECTED",
        "code": "INVALID_STATE",
        "current_status": "APPROVED",
        "reason": "INVALID_STATE"
      },
      "entity_id": "1",
      "entity_type": "deprovision_request",
      "event": "DEPROVISION_REJECT_DENIED",
      "id": 11,
      "ts": "2026-10-22T05:11:00Z"
    }
  ],
  "meta": {
    "count": 5
  }
}
```
Audit events: `DEPROVISION_PREPARED`, `DEPROVISION_APPROVED`, `DEPROVISION_REJECTED`, `DEPROVISION_DECISION_REPLAYED`,
and for refused attempts `DEPROVISION_PREPARE_DENIED`, `DEPROVISION_APPROVE_DENIED`, `DEPROVISION_REJECT_DENIED`
(each with `detail.reason`). Refused prepare attempts are filed under `entity_type=finding`; everything else under
`entity_type=deprovision_request`. Requests missing the `X-Actor` header or with a malformed body are rejected before
any domain action and are not audited (there is no actor to attribute them to).


---

# Stage 4 & 5: Execution, Independent Verification & Frontend Contract

## POST /deprovision-requests/{id}/execute

Executes an approved request, running mandatory pre-execution checks against live sources, disabling the account, and performing an independent fresh read to verify the outcome.

**Headers:**
- `X-Actor: operator@acme.example` (required)

**Request Body:** None.

**Response (HTTP 200) - Success (VERIFIED):**
```json
{
  "data": {
    "action": "DISABLE",
    "decided_at": "2026-10-23T14:30:00Z",
    "decided_by": "approver@acme.example",
    "decision_note": "Confirmed with HR",
    "executed_at": "2026-10-23T14:35:10Z",
    "executions": [
      {
        "attempted_at": "2026-10-23T14:35:10Z",
        "claimed_success": true,
        "connector_response": {
          "message": "Account disabled",
          "raw": {
            "status": "disabled"
          },
          "success": true
        },
        "id": 1
      }
    ],
    "expected_status": "DISABLED",
    "external_account_id": "S-1001",
    "finding": {
      "account": {
        "account_type": "INDIVIDUAL",
        "display_name": "Rahul Sharma",
        "email": "rahul.sharma@acme.example",
        "employee_id": "E101",
        "external_account_id": "S-1001",
        "id": 1,
        "last_login_at": "2026-10-01T08:30:00Z",
        "status": "ACTIVE",
        "system": "Slack",
        "username": "rahul.sharma"
      },
      "classification": "LEAVER_ACTIVE",
      "employee": {
        "department": "Engineering",
        "employee_id": "E101",
        "employment_status": "TERMINATED",
        "full_name": "Rahul Sharma",
        "termination_date": "2026-09-30",
        "work_email": "rahul.sharma@acme.example"
      },
      "id": 1,
      "match_confidence": "HIGH",
      "match_method": "WORK_EMAIL",
      "reason": "Employee terminated 2026-09-30 but account is still ACTIVE",
      "scan_id": 1
    },
    "finding_id": 1,
    "id": 1,
    "idempotency_key": "deprov-1-...",
    "prepared_at": "2026-10-23T14:20:00Z",
    "prepared_by": "preparer@acme.example",
    "status": "VERIFIED",
    "system": "Slack",
    "verifications": [
      {
        "id": 1,
        "observed_at": "2026-10-23T14:35:11Z",
        "observed_status": "DISABLED",
        "passed": true,
        "raw": {
          "account_type": "INDIVIDUAL",
          "display_name": "Rahul Sharma",
          "email": "rahul.sharma@acme.example",
          "employee_id": "E101",
          "external_account_id": "S-1001",
          "last_login_at": "2026-10-01T08:30:00Z",
          "status": "DISABLED",
          "system": "Slack",
          "username": "rahul.sharma"
        }
      }
    ],
    "verified": true,
    "verified_at": "2026-10-23T14:35:11Z"
  },
  "meta": {
    "idempotent_replay": false
  }
}
```

### Idempotent Replay (HTTP 200)
When executed on an already `VERIFIED` request, returns the same payload with `"meta": {"idempotent_replay": true}`.

### Verification Failure (HTTP 200)
When the connector claims success but independent verification observes the account is still `ACTIVE` (e.g. `silent_noop` fault):
- `status`: `"VERIFICATION_FAILED"`
- `verified`: `false`
- `executions[0].claimed_success`: `true`
- `verifications[0].passed`: `false`
- `verifications[0].observed_status`: `"ACTIVE"`

### Pre-Execution Check Abort (HTTP 409)
When live HR status is no longer `TERMINATED` or SaaS account is not `ACTIVE`:
```json
{
  "error": {
    "code": "STALE_STATE",
    "message": "Pre-execution check failed: employee E101 is ACTIVE, not TERMINATED (status changed or employee rehired)",
    "details": {
      "employee_id": "E101",
      "current_employment_status": "ACTIVE"
    }
  }
}
```

### Stage 4/5 Audit Events Added
| Event | Entity Type | Details |
|---|---|---|
| `DEPROVISION_EXECUTE_DENIED` | `deprovision_request` | Refused attempt (wrong state, pre-check failure) |
| `DEPROVISION_EXECUTING` | `deprovision_request` | Atomic transition into execution |
| `DEPROVISION_EXECUTED` | `deprovision_request` | Executor claim recorded (`claim` payload) |
| `DEPROVISION_VERIFIED` | `deprovision_request` | Independent fresh read confirmed DISABLED |
| `DEPROVISION_VERIFICATION_FAILED` | `deprovision_request` | Independent fresh read observed non-DISABLED state |
| `DEPROVISION_EXECUTION_FAILED` | `deprovision_request` | Connector error or reject |
| `DEPROVISION_EXECUTION_REPLAYED` | `deprovision_request` | Re-execution of verified request |

