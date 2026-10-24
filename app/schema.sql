-- Leaver Access Review Auditor: SQLite schema (Stage 1).
-- Timestamps are ISO-8601 UTC text. Enum-like columns are protected by CHECK constraints.

CREATE TABLE IF NOT EXISTS employees (
  employee_id        TEXT PRIMARY KEY,
  full_name          TEXT NOT NULL,
  work_email         TEXT NOT NULL,
  employment_status  TEXT NOT NULL CHECK (employment_status IN ('ACTIVE','TERMINATED')),
  termination_date   TEXT,
  department         TEXT
);
CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(lower(work_email));

CREATE TABLE IF NOT EXISTS scans (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at   TEXT NOT NULL,
  finished_at  TEXT,
  connector    TEXT NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('RUNNING','COMPLETED','FAILED')),
  summary_json TEXT
);

CREATE TABLE IF NOT EXISTS accounts (               -- snapshot per scan
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id             INTEGER NOT NULL REFERENCES scans(id),
  system              TEXT NOT NULL,
  external_account_id TEXT NOT NULL,
  email               TEXT,
  display_name        TEXT,
  username            TEXT,
  employee_id         TEXT,                          -- only if the source system provides it
  account_type        TEXT NOT NULL CHECK (account_type IN ('INDIVIDUAL','SHARED','SERVICE')),
  status              TEXT NOT NULL,
  last_login_at       TEXT,                          -- NULL = unavailable, never guessed
  raw_json            TEXT
);
CREATE INDEX IF NOT EXISTS idx_accounts_scan ON accounts(scan_id);

CREATE TABLE IF NOT EXISTS exclusions (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  system              TEXT NOT NULL,
  external_account_id TEXT NOT NULL,
  reason              TEXT NOT NULL,
  added_by            TEXT NOT NULL,
  added_at            TEXT NOT NULL,
  UNIQUE (system, external_account_id)
);

CREATE TABLE IF NOT EXISTS findings (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id          INTEGER NOT NULL REFERENCES scans(id),
  account_id       INTEGER NOT NULL REFERENCES accounts(id),
  employee_id      TEXT REFERENCES employees(employee_id),
  classification   TEXT NOT NULL CHECK (classification IN
                     ('LEAVER_ACTIVE','EXCLUDED','NEEDS_REVIEW','NO_MATCH','OK')),
  match_method     TEXT CHECK (match_method IN ('WORK_EMAIL','EMPLOYEE_ID','NAME_ONLY')),
  match_confidence TEXT CHECK (match_confidence IN ('HIGH','LOW')),
  reason           TEXT,
  created_at       TEXT NOT NULL,
  UNIQUE (scan_id, account_id)
);
CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id, classification);

CREATE TABLE IF NOT EXISTS evidence (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  finding_id  INTEGER NOT NULL REFERENCES findings(id),
  type        TEXT NOT NULL CHECK (type IN
                ('HR_RECORD','ACCOUNT_RECORD','MATCH_RATIONALE','EXCLUSION_RULE','LAST_LOGIN')),
  detail_json TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deprovision_requests (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  finding_id          INTEGER NOT NULL REFERENCES findings(id),
  system              TEXT NOT NULL,
  external_account_id TEXT NOT NULL,
  action              TEXT NOT NULL DEFAULT 'DISABLE'  CHECK (action = 'DISABLE'),          -- disable-only, enforced in DB
  expected_status     TEXT NOT NULL DEFAULT 'DISABLED' CHECK (expected_status = 'DISABLED'),
  status              TEXT NOT NULL CHECK (status IN
                        ('PREPARED','APPROVED','REJECTED','EXECUTING','EXECUTION_FAILED',
                         'EXECUTED_UNVERIFIED','VERIFIED','VERIFICATION_FAILED')),
  idempotency_key     TEXT NOT NULL UNIQUE,
  prepared_by         TEXT NOT NULL,
  prepared_at         TEXT NOT NULL,
  decided_by          TEXT,
  decided_at          TEXT,
  decision_note       TEXT,
  executed_at         TEXT,
  verified_at         TEXT
);
-- At most one open request per finding; failed/rejected ones may be re-prepared.
CREATE UNIQUE INDEX IF NOT EXISTS one_open_request_per_finding
  ON deprovision_requests(finding_id)
  WHERE status NOT IN ('REJECTED','EXECUTION_FAILED','VERIFICATION_FAILED');

-- ...and at most one open request per ACCOUNT, even across scans (a rescan creates new finding rows).
CREATE UNIQUE INDEX IF NOT EXISTS one_open_request_per_account
  ON deprovision_requests(system, external_account_id)
  WHERE status NOT IN ('REJECTED','EXECUTION_FAILED','VERIFICATION_FAILED');

-- Defence in depth: whatever the application code does, no request past PREPARED (other than REJECTED)
-- may carry an approver that is missing or equals the preparer (case-insensitive).
CREATE TRIGGER IF NOT EXISTS deprovision_separation_of_duties
BEFORE UPDATE ON deprovision_requests
WHEN NEW.status NOT IN ('PREPARED','REJECTED')
 AND (NEW.decided_by IS NULL OR lower(NEW.decided_by) = lower(NEW.prepared_by))
BEGIN SELECT RAISE(ABORT, 'separation of duties: approver must differ from preparer'); END;

CREATE TABLE IF NOT EXISTS executions (               -- what the connector CLAIMED. Not proof.
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id              INTEGER NOT NULL REFERENCES deprovision_requests(id),
  attempted_at            TEXT NOT NULL,
  connector_response_json TEXT,
  claimed_success         INTEGER NOT NULL CHECK (claimed_success IN (0,1))
);

CREATE TABLE IF NOT EXISTS verifications (            -- independent fresh read from the connector
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id      INTEGER NOT NULL REFERENCES deprovision_requests(id),
  observed_at     TEXT NOT NULL,
  observed_status TEXT,
  passed          INTEGER NOT NULL CHECK (passed IN (0,1)),
  raw_json        TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT NOT NULL,
  actor       TEXT NOT NULL,
  event       TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id   TEXT NOT NULL,
  detail_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);

-- Append-only in normal operation. (The demo-only reset drops and recreates the whole schema.)
CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
