# Leaver Access Review Auditor: backend (Stage 5 - Demo Ready)

Flask + SQLite. Synthetic Slack/GitHub/Jira data until the official mock admin console exists.
Disable-only: there is no delete capability anywhere in the code or schema.

## Setup (Python 3.10+)

macOS / Linux:
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Windows PowerShell:
    py -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt

## Run (local demo)

macOS / Linux:
    export DEMO_MODE=1
    export FRONTEND_ORIGIN=http://localhost:5173
    export APPROVER_ACTORS=approver@acme.example,approver2@acme.example
    python run.py

Windows PowerShell:
    $env:DEMO_MODE="1"; $env:FRONTEND_ORIGIN="http://localhost:5173"
    $env:APPROVER_ACTORS="approver@acme.example,approver2@acme.example"
    python run.py

API base URL: http://127.0.0.1:5001/api/v1

| Variable | Default | Meaning |
|---|---|---|
| CONNECTOR | synthetic | `synthetic` or `mock_admin` (mock_admin not implemented yet; startup fails clearly) |
| DEMO_MODE | 0 | `1` enables /dev/* endpoints. Without it they do not exist (404) |
| FRONTEND_ORIGIN | (empty = no CORS) | Exact origin(s), comma-separated. `*` is rejected |
| DATABASE_PATH | instance/auditor.sqlite3 | SQLite file |
| APPROVER_ACTORS | (empty) | Comma-separated identities allowed to approve/reject, e.g. `approver@acme.example`. **Empty = nobody can approve** (fails closed). Case-insensitive; no wildcards |
| HOST / PORT | 127.0.0.1 / 5001 | DEMO_MODE refuses non-loopback HOST unless ALLOW_LAN_DEMO=1 |

Run a single server process: synthetic SaaS state lives in memory.

## Test

    python -m pytest -v
    # no pytest? the same tests also run with the standard library:
    python -m unittest discover -s tests -t . -v

## Stage 2: scanning, matching, findings

    curl -X POST -H 'X-Actor: you@acme.example' http://127.0.0.1:5001/api/v1/scans
    curl http://127.0.0.1:5001/api/v1/findings?classification=LEAVER_ACTIVE
    curl http://127.0.0.1:5001/api/v1/summary

A scan is **read-only**: it reads HR + SaaS accounts, matches identities, classifies each account and stores
findings with evidence. It never disables or changes any account. Deprovisioning arrives in Stages 3-4.

Matching order: verified work email (HIGH) -> employee_id on the account (HIGH) -> name only (LOW, always
NEEDS_REVIEW, never eligible). Conflicting or ambiguous signals are NEEDS_REVIEW. Shared/service accounts
(source-marked SHARED/SERVICE, or listed in the exclusions table) are EXCLUDED and never matched.
Explicit exclusions load from `data/synthetic/exclusions.json` on first startup if the table is empty.

Full contract with real sample JSON: `docs/api.md`.

## Stage 3: deprovisioning requests (prepare, approve, reject)

    # 1. a scan, then prepare a request for an eligible leaver (any actor may prepare)
    curl -X POST -H 'X-Actor: preparer@acme.example' http://127.0.0.1:5001/api/v1/scans
    curl -X POST -H 'X-Actor: preparer@acme.example' http://127.0.0.1:5001/api/v1/findings/1/deprovision-requests
    # 2. a DIFFERENT, allowlisted person approves (or rejects)
    curl -X POST -H 'X-Actor: approver@acme.example' -H 'Content-Type: application/json' \
         -d '{"note":"Confirmed with HR"}' http://127.0.0.1:5001/api/v1/deprovision-requests/1/approve
    # 3. read the trail
    curl 'http://127.0.0.1:5001/api/v1/audit-log?entity_type=deprovision_request&entity_id=1'

## Stage 4: execution and independent verification

    # 1. execute an approved request (needs X-Actor)
    curl -X POST -H 'X-Actor: operator@acme.example' \
         http://127.0.0.1:5001/api/v1/deprovision-requests/1/execute

    # 2. inspect verified request with executions[] and verifications[]
    curl http://127.0.0.1:5001/api/v1/deprovision-requests/1

    # 3. check updated dashboard (verified count increments)
    curl http://127.0.0.1:5001/api/v1/summary

Stage 4 enforces:
1. Only APPROVED requests can be executed.
2. Mandatory pre-checks immediately before execution: live HR status must still be TERMINATED, and live SaaS account must still be ACTIVE.
3. Independent post-execution verification: fresh read from connector (never trusts claimed success alone).
4. Idempotent execution (safe re-execution of VERIFIED requests).
5. Safe retry: failed requests (EXECUTION_FAILED / VERIFICATION_FAILED) free the account so a new request can be prepared and approved.

## Stage 5: integration, demo runbook & mock-admin boundary

A dedicated, complete step-by-step interactive runbook is available in [`docs/demo_runbook.md`](docs/demo_runbook.md).
It walks through:
- System reset & baseline health verification.
- Account scanning & identity matching.
- Reviewing leavers and rich evidence (including surname-change handling).
- Honoring explicit shared & service exclusions.
- Separation-of-duties and allowlist safeguards.
- Approved execution & independent post-execution verification.
- Fault-injection demonstration (`silent_noop` lying console detection).
- Safe retry workflows and immutable audit trail inspection.

### Mock Admin Connector Boundary Notice
The official mock admin console URL, credentials, and access protocols have not been provided yet.
In accordance with hackathon safety requirements, the backend does not invent a fictional external endpoint
or attempt unauthorized access. `CONNECTOR=synthetic` remains the active, tested integration.
Starting with `CONNECTOR=mock_admin` continues to fail loudly with a clear message explaining that
the official integration details are pending.


## Endpoints (base /api/v1)

| Method | Path | Notes |
|---|---|---|
| POST | /scans | needs X-Actor. Read-only scan |
| GET | /scans, /scans/{id} | scan history / detail |
| GET | /findings, /findings/{id} | list (latest scan by default) / detail with evidence |
| GET | /summary | dashboard counts |
| POST | /findings/{id}/deprovision-requests | prepare (needs X-Actor) |
| GET | /deprovision-requests, /deprovision-requests/{id} | list / detail |
| POST | /deprovision-requests/{id}/approve, /reject | approver allowlist + separation of duties |
| POST | /deprovision-requests/{id}/execute | execute approved request + independent verification |
| GET | /audit-log | append-only trail |
| GET | /whoami | `{actor, can_approve}` UI hint |

### Stage 1 endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /health | always available |
| POST | /dev/reset | DEMO_MODE only, needs X-Actor. Wipes DB and audit log, reseeds, resets synthetic SaaS |
| GET | /dev/connector/accounts | DEMO_MODE only. Live connector state, not from our DB |
| GET / POST / DELETE | /dev/fault-injection | DEMO_MODE only. POST/DELETE need X-Actor. Body: `{"mode": "none|silent_noop|error|reject", "system": "Slack", "external_account_id": "S-1001"}` (target optional) |

Errors: `{"error": {"code": "...", "message": "..."}}`.
X-Actor is a demo-only label for the audit log, NOT authentication.
