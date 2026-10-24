# Leaver Access Review Auditor: Stage 5 Demo Runbook

This runbook provides a complete, copy-pasteable demonstration of the Leaver Access Review Auditor backend.

---

## 1. Environment & Setup

### Environment Variables
| Variable | Value for Demo | Description |
|---|---|---|
| `DEMO_MODE` | `1` | Enables `/api/v1/dev/*` endpoints (reset, fault injection, live connector reads) |
| `APPROVER_ACTORS` | `approver@acme.example,approver2@acme.example` | Allowlisted approver emails (case-insensitive) |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed CORS origin for local React/Vite frontend |
| `HOST` / `PORT` | `127.0.0.1` / `5001` | Server binding (loopback required when DEMO_MODE=1) |
| `CONNECTOR` | `synthetic` | Built-in high-fidelity in-memory connector |
| `HR_SOURCE` | `synthetic` | Built-in HR employee source of truth |

### Starting the Server
```bash
cd ~/Downloads/leaver-auditor
source .venv/bin/activate

export DEMO_MODE=1
export FRONTEND_ORIGIN=http://localhost:5173
export APPROVER_ACTORS=approver@acme.example,approver2@acme.example
export HOST=127.0.0.1
export PORT=5001

python run.py
```

Expected startup message:
```text
approvers=2 connector=synthetic demo_mode=True cors_origins=['http://localhost:5173'] db=...
* Running on http://127.0.0.1:5001
```

---

## 2. Demo Walkthrough (Step-by-Step)

Open a new terminal window for `curl` commands.

### Step 1: Health & Role Inspection
Verify that the service is running and inspect actor permissions:

```bash
# Check service health
curl -s http://127.0.0.1:5001/api/v1/health | jq

# Check if preparer can approve (cosmetic UI hint)
curl -s -H 'X-Actor: preparer@acme.example' http://127.0.0.1:5001/api/v1/whoami | jq
# => "can_approve": false

# Check if allowlisted approver can approve
curl -s -H 'X-Actor: approver@acme.example' http://127.0.0.1:5001/api/v1/whoami | jq
# => "can_approve": true
```

---

### Step 2: Reset Demo State
Wipes SQLite database, reseeds employees and exclusions, and resets synthetic SaaS accounts to their pristine state:

```bash
curl -s -X POST -H 'X-Actor: demo@acme.example' http://127.0.0.1:5001/api/v1/dev/reset | jq
```

Verify initial dashboard counts:
```bash
curl -s http://127.0.0.1:5001/api/v1/summary | jq
```
Expected: `total_findings: 0`, `pending_approval: 0`, `verified: 0`.

---

### Step 3: Trigger a Read-Only Scan
Executes identity matching across all systems without mutating any accounts:

```bash
curl -s -X POST -H 'X-Actor: auditor@acme.example' http://127.0.0.1:5001/api/v1/scans | jq
```

Verify dashboard summary after scan:
```bash
curl -s http://127.0.0.1:5001/api/v1/summary | jq
```
Expected breakdown across 16 synthetic accounts:
- `total_findings`: 16
- `leavers_active`: 7
- `excluded`: 4
- `needs_review`: 1
- `findings_by_classification.OK`: 4

---

### Step 4: Inspect Findings & Audit Evidence

#### 4A. List Leaver Findings
```bash
curl -s 'http://127.0.0.1:5001/api/v1/findings?classification=LEAVER_ACTIVE' | jq
```

#### 4B. Surname Change Match (Priya Sharma vs Priya Nair)
Priya's work email `priya.sharma@acme.example` verified her identity despite HR record name change to Priya Nair:
```bash
# Inspect finding 2 (Priya's Slack account S-1002)
curl -s http://127.0.0.1:5001/api/v1/findings/2 | jq
```
Notice evidence array containing `HR_RECORD`, `ACCOUNT_RECORD`, `MATCH_RATIONALE`, and `LAST_LOGIN`.

#### 4C. Explicit Shared / Service Account Exclusions
```bash
curl -s 'http://127.0.0.1:5001/api/v1/findings?classification=EXCLUDED' | jq
```
Notice `deprovision_eligible: false` and exclusion rationale.

---

### Step 5: Prepare a Deprovision Request
Prepare a disable request for Rahul Sharma's Slack account (`finding_id = 1`, `S-1001`):

```bash
curl -s -X POST -H 'X-Actor: preparer@acme.example' \
  http://127.0.0.1:5001/api/v1/findings/1/deprovision-requests | jq
```
Expected: HTTP 201, `status: "PREPARED"`, `action: "DISABLE"`, `expected_status: "DISABLED"`.
Notice: Account in Slack is **still ACTIVE** (preparation never touches accounts).

---

### Step 6: Approval Safeguards & Separation of Duties

#### 6A. Prevent Self-Approval
If an allowlisted approver prepares a request, they cannot approve it:
```bash
# Prepare request as approver@acme.example for Priya (finding 2)
curl -s -X POST -H 'X-Actor: approver@acme.example' \
  http://127.0.0.1:5001/api/v1/findings/2/deprovision-requests | jq '.data.id'
# (Assume id is 2)

# Attempt self-approval:
curl -s -X POST -H 'X-Actor: approver@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/2/approve | jq
```
Expected response: HTTP 403 `SELF_APPROVAL_FORBIDDEN`.

#### 6B. Prevent Unauthorized Approval
```bash
curl -s -X POST -H 'X-Actor: mallory@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/1/approve | jq
```
Expected response: HTTP 403 `APPROVER_NOT_AUTHORIZED`.

#### 6C. Valid Human Approval
Allowlisted approver approves request 1 with rationale:
```bash
curl -s -X POST -H 'X-Actor: approver@acme.example' -H 'Content-Type: application/json' \
  -d '{"note": "Confirmed termination date 2026-09-30 with HR"}' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/1/approve | jq
```
Expected response: HTTP 200, `status: "APPROVED"`, `decided_by: "approver@acme.example"`.

---

### Step 7: Execution & Independent Verification

Execute the approved request:
```bash
curl -s -X POST -H 'X-Actor: operator@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/1/execute | jq
```

Expected response (HTTP 200):
```json
{
  "data": {
    "id": 1,
    "status": "VERIFIED",
    "verified": true,
    "executed_at": "2026-10-...",
    "verified_at": "2026-10-...",
    "executions": [
      {
        "claimed_success": true,
        "connector_response": {
          "message": "Account disabled",
          "raw": {"status": "disabled"},
          "success": true
        }
      }
    ],
    "verifications": [
      {
        "passed": true,
        "observed_status": "DISABLED"
      }
    ]
  },
  "meta": {
    "idempotent_replay": false
  }
}
```

Check ground-truth connector status:
```bash
curl -s http://127.0.0.1:5001/api/v1/dev/connector/accounts | jq '.data[] | select(.external_account_id=="S-1001")'
```
Status is now verified `DISABLED`.

---

### Step 8: Safe Replay & Idempotency
Call execute again on the verified request:
```bash
curl -s -X POST -H 'X-Actor: operator@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/1/execute | jq
```
Expected response: HTTP 200, `"meta": {"idempotent_replay": true}`. No secondary connector execution occurred.

---

### Step 9: Fault Injection Demo (Lying Console / Verification Failure)

Inject a `silent_noop` fault where the console claims success but leaves the account active:
```bash
curl -s -X POST -H 'X-Actor: demo@acme.example' -H 'Content-Type: application/json' \
  -d '{"mode": "silent_noop", "system": "GitHub", "external_account_id": "G-2001"}' \
  http://127.0.0.1:5001/api/v1/dev/fault-injection | jq
```

Prepare, approve and execute request for `G-2001` (finding 3):
```bash
# 1. Prepare
curl -s -X POST -H 'X-Actor: preparer@acme.example' \
  http://127.0.0.1:5001/api/v1/findings/3/deprovision-requests | jq '.data.id'
# (Assume id is 3)

# 2. Approve
curl -s -X POST -H 'X-Actor: approver@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/3/approve | jq '.data.status'

# 3. Execute
curl -s -X POST -H 'X-Actor: operator@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/3/execute | jq
```

Notice:
- `status`: `"VERIFICATION_FAILED"`
- `verified`: `false`
- `executions[0].claimed_success`: `true` (console lied!)
- `verifications[0].passed`: `false`, `observed_status`: `"ACTIVE"` (caught by independent fresh read!)

#### Recovery / Safe Retry:
```bash
# 1. Clear faults
curl -s -X DELETE -H 'X-Actor: demo@acme.example' http://127.0.0.1:5001/api/v1/dev/fault-injection | jq

# 2. Re-prepare new request for finding 3 (allowed because previous request is closed)
curl -s -X POST -H 'X-Actor: preparer@acme.example' \
  http://127.0.0.1:5001/api/v1/findings/3/deprovision-requests | jq '.data.id'
# (Assume new id is 4)

# 3. Approve and execute
curl -s -X POST -H 'X-Actor: approver@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/4/approve | jq '.data.status'

curl -s -X POST -H 'X-Actor: operator@acme.example' \
  http://127.0.0.1:5001/api/v1/deprovision-requests/4/execute | jq '.data.status'
# => "VERIFIED"
```

---

### Step 10: Inspect Complete Audit Trail
Query the immutable audit trail for the entire lifecycle:
```bash
curl -s 'http://127.0.0.1:5001/api/v1/audit-log?limit=50' | jq
```
All events (`SCAN_STARTED`, `SCAN_COMPLETED`, `DEPROVISION_PREPARED`, `DEPROVISION_APPROVED`, `DEPROVISION_EXECUTING`, `DEPROVISION_EXECUTED`, `DEPROVISION_VERIFIED`, `DEPROVISION_VERIFICATION_FAILED`) are chronologically indexed with actor, timestamp, entity ID, and context details.

---

## 3. Frontend Integration Reference

| Action | HTTP Method | Endpoint | Headers | Request Body | Response Status |
|---|---|---|---|---|---|
| Check User Role | `GET` | `/api/v1/whoami` | `X-Actor: email` | None | `200` (`{data: {actor, can_approve}}`) |
| Dashboard Summary | `GET` | `/api/v1/summary` | None | None | `200` (`{data: {findings_by_classification, ...}}`) |
| Trigger Scan | `POST` | `/api/v1/scans` | `X-Actor: email` | None | `201` (`{data: scan_obj}`) |
| List Findings | `GET` | `/api/v1/findings?classification=LEAVER_ACTIVE` | None | None | `200` (`{data: findings_list}`) |
| Finding Detail | `GET` | `/api/v1/findings/{id}` | None | None | `200` (`{data: finding_with_evidence}`) |
| Prepare Request | `POST` | `/api/v1/findings/{id}/deprovision-requests` | `X-Actor: email` | None | `201` (`{data: request_obj}`) |
| Approve Request | `POST` | `/api/v1/deprovision-requests/{id}/approve` | `X-Actor: approver` | `{"note": "..."}` (optional) | `200` (`{data: request_obj, meta: {...}}`) |
| Reject Request | `POST` | `/api/v1/deprovision-requests/{id}/reject` | `X-Actor: approver` | `{"note": "..."}` (optional) | `200` (`{data: request_obj, meta: {...}}`) |
| Execute Request | `POST` | `/api/v1/deprovision-requests/{id}/execute` | `X-Actor: operator` | None | `200` (`{data: request_obj, meta: {...}}`) |
| Audit Trail | `GET` | `/api/v1/audit-log?entity_type=...&entity_id=...` | None | None | `200` (`{data: audit_rows}`) |

---

## 4. Troubleshooting Guide

| Issue / Error | Cause | Resolution |
|---|---|---|
| `400 ACTOR_REQUIRED` | Missing `X-Actor` header on POST/DELETE or `/whoami` | Add `-H 'X-Actor: your_name@acme.example'` |
| `403 APPROVER_NOT_AUTHORIZED` | Actor is not listed in `APPROVER_ACTORS` environment variable | Ensure actor matches one in `APPROVER_ACTORS` |
| `403 SELF_APPROVAL_FORBIDDEN` | The approver is the same person who prepared the request | Have a different allowlisted approver approve the request |
| `404 NOT_FOUND` | Finding, request ID, or demo endpoint not found | Verify ID exists; if `/dev/*`, ensure `DEMO_MODE=1` is set |
| `409 DUPLICATE_REQUEST` | An open request already exists for this SaaS account | Look up the existing request or use a different account |
| `409 STALE_STATE` | Live HR employee is active/missing or live SaaS account is not active | Pre-execution safety check aborted execution; verify source state |
| `409 INVALID_STATE` | Request is in wrong state (e.g. executing a PREPARED request) | Only `APPROVED` requests can be executed |
| CORS Origin Error | Frontend browser origin blocked | Set `FRONTEND_ORIGIN=http://localhost:5173` before starting `run.py` |
| `ConfigError: Refusing to bind ... with DEMO_MODE=1` | Host set to `0.0.0.0` with `DEMO_MODE=1` | Demo mode binds to `127.0.0.1` by default for security |
